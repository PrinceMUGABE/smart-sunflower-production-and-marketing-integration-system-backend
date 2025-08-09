from decimal import Decimal, InvalidOperation
import re
import traceback
import requests
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.conf import settings

from .models import Order
from warehouseApp.models import Warehouse, Category, Commodity, WarehouseCommodity
from userApp.models import CustomUser

from .serializers import (
    OrderSerializer, OrderUpdateSerializer, OrderActionSerializer,
    WarehouseCapacitySerializer, OrderPaymentSerializer
)

from paypack.client import HttpClient
from paypack.transactions import Transaction

# Initialize PayPack client
client_id = "b4425b30-3a0b-11f0-8ab2-dead131a2dd9"
client_secret = "01673878877c7835174e83943a68504eda39a3ee5e6b4b0d3255bfef95601890afd80709"

try:
    HttpClient(client_id=client_id, client_secret=client_secret)
except Exception as e:
    print(f"Warning: PayPack client initialization failed: {e}")


def process_payment(amount, phone_number):
    """
    Process payment with proper error handling and retry logic
    """
    try:
        # Validate amount
        if amount <= 0:
            return {
                'success': False,
                'message': 'Payment amount must be greater than zero',
                'error_code': 'INVALID_AMOUNT'
            }
        
        # Validate phone number format
        if not re.match(r'^\+?[0-9]{9,15}$', phone_number):
            return {
                'success': False,
                'message': 'Invalid phone number format',
                'error_code': 'INVALID_PHONE'
            }
        
        print(f"Processing payment: Amount={amount}, Phone={phone_number}")
        
        # Initialize transaction
        transaction_client = Transaction()
        
        # Process the payment
        cashin_result = transaction_client.cashin(
            amount=float(amount), 
            phone_number=phone_number
        )
        
        print(f"Payment result: {cashin_result}")
        
        # Handle different payment statuses
        # Check if cashin_result is a dictionary or has attributes
        if isinstance(cashin_result, dict):
            # Handle dictionary response
            payment_status = cashin_result.get('status')
            if payment_status == 'success':
                return {
                    'success': True,
                    'message': 'Payment processed successfully',
                    'transaction_id': cashin_result.get('ref') or cashin_result.get('transaction_id'),
                    'payment_status': 'completed',
                    'data': cashin_result
                }
            elif payment_status == 'pending':
                return {
                    'success': True,
                    'message': 'Payment is pending confirmation',
                    'transaction_id': cashin_result.get('ref') or cashin_result.get('transaction_id'),
                    'payment_status': 'pending',
                    'data': cashin_result
                }
            elif payment_status in ['failed', 'cancelled', 'rejected']:
                return {
                    'success': False,
                    'message': cashin_result.get('message', f'Payment {payment_status}'),
                    'error_code': 'PAYMENT_FAILED',
                    'payment_status': payment_status,
                    'data': cashin_result
                }
            elif 'ref' in cashin_result:
                # If we have a ref but no explicit status, assume pending
                return {
                    'success': True,
                    'message': 'Payment initiated successfully',
                    'transaction_id': cashin_result.get('ref'),
                    'payment_status': 'pending',
                    'data': cashin_result
                }
            else:
                return {
                    'success': False,
                    'message': 'Payment failed - unexpected response format',
                    'error_code': 'PAYMENT_FAILED',
                    'data': cashin_result
                }
        else:
            # Handle object response (legacy support)
            if hasattr(cashin_result, 'status'):
                if cashin_result.status == 'success':
                    return {
                        'success': True,
                        'message': 'Payment processed successfully',
                        'transaction_id': getattr(cashin_result, 'transaction_id', None),
                        'payment_status': 'completed',
                        'data': cashin_result
                    }
                elif cashin_result.status == 'pending':
                    return {
                        'success': True,
                        'message': 'Payment is pending confirmation',
                        'transaction_id': getattr(cashin_result, 'transaction_id', None),
                        'payment_status': 'pending',
                        'data': cashin_result
                    }
                else:
                    return {
                        'success': False,
                        'message': getattr(cashin_result, 'message', f'Payment {cashin_result.status}'),
                        'error_code': 'PAYMENT_FAILED',
                        'payment_status': cashin_result.status,
                        'data': cashin_result
                    }
            elif hasattr(cashin_result, 'ref'):
                return {
                    'success': True,
                    'message': 'Payment initiated successfully',
                    'transaction_id': getattr(cashin_result, 'ref', None),
                    'payment_status': 'pending',
                    'data': cashin_result
                }
            else:
                return {
                    'success': False,
                    'message': 'Payment failed - unexpected response format',
                    'error_code': 'PAYMENT_FAILED',
                    'data': cashin_result
                }
            
    except requests.exceptions.ConnectionError as e:
        print(f"Network connection error during payment: {e}")
        return {
            'success': False,
            'message': 'Unable to connect to payment service. Please check your internet connection and try again.',
            'error_code': 'NETWORK_ERROR',
            'technical_error': str(e)
        }
    except requests.exceptions.Timeout as e:
        print(f"Payment request timeout: {e}")
        return {
            'success': False,
            'message': 'Payment request timed out. Please try again.',
            'error_code': 'TIMEOUT_ERROR',
            'technical_error': str(e)
        }
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error during payment: {e}")
        return {
            'success': False,
            'message': 'Payment service error. Please try again later.',
            'error_code': 'HTTP_ERROR',
            'technical_error': str(e)
        }
    except Exception as e:
        print(f"Unexpected payment error: {e}")
        return {
            'success': False,
            'message': 'An unexpected error occurred during payment processing.',
            'error_code': 'UNKNOWN_ERROR',
            'technical_error': str(e)
        }


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_order(request):
    """Create a new order with comprehensive validation and improved payment handling"""
    print("\n=== Starting order creation process ===")
    print("Received data:", request.data)
    
    try:
        # Validate required fields are present
        required_fields = ['origin', 'warehouse', 'category', 'commodity', 'quantity', 'phone_number', 'cost_charged']
        missing_fields = [field for field in required_fields if field not in request.data]
        
        if missing_fields:
            error_msg = f"Missing required fields: {', '.join(missing_fields)}"
            print(f"Validation Error: {error_msg}")
            return Response({
                'success': False,
                'message': error_msg,
                'missing_fields': missing_fields
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Convert numeric fields to proper types
        try:
            data = request.data.copy()
            numeric_fields = ['warehouse', 'category', 'commodity']
            
            for field in numeric_fields:
                if field in data:
                    data[field] = int(data[field])
            
            if 'quantity' in data:
                data['quantity'] = Decimal(str(data['quantity']))
                
            if 'cost_charged' in data:
                data['cost_charged'] = Decimal(str(data['cost_charged']))
                
        except (ValueError, InvalidOperation) as e:
            error_msg = f"Invalid numeric value: {str(e)}"
            print(f"Validation Error: {error_msg}")
            return Response({
                'success': False,
                'message': error_msg,
                'error': 'invalid_numeric_value'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate phone number format
        phone_number = data.get('phone_number', '')
        if not re.match(r'^\+?[0-9]{9,15}$', phone_number):
            error_msg = "Invalid phone number format. Please use a valid international format."
            print(f"Validation Error: {error_msg}")
            return Response({
                'success': False,
                'message': error_msg,
                'error': 'invalid_phone_number'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate cost_charged
        cost_charged = data.get('cost_charged')
        if cost_charged <= 0:
            error_msg = "Cost charged must be greater than zero"
            print(f"Validation Error: {error_msg}")
            return Response({
                'success': False,
                'message': error_msg,
                'error': 'invalid_cost'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if referenced objects exist
        try:
            warehouse = Warehouse.objects.get(id=data['warehouse'])
            category = Category.objects.get(id=data['category'])
            commodity = Commodity.objects.get(id=data['commodity'])
            
            # Verify commodity belongs to category
            if commodity.category != category:
                error_msg = f"Commodity {commodity.name} does not belong to category {category.name}"
                print(f"Validation Error: {error_msg}")
                return Response({
                    'success': False,
                    'message': error_msg,
                    'error': 'invalid_commodity_category'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            # Verify warehouse supports this commodity
            if not WarehouseCommodity.objects.filter(warehouse=warehouse, commodity=commodity).exists():
                error_msg = f"Warehouse {warehouse.location} does not support commodity {commodity.name}"
                print(f"Validation Error: {error_msg}")
                return Response({
                    'success': False,
                    'message': error_msg,
                    'error': 'warehouse_commodity_mismatch'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except (Warehouse.DoesNotExist, Category.DoesNotExist, Commodity.DoesNotExist) as e:
            error_msg = f"Invalid reference: {str(e)}"
            print(f"Validation Error: {error_msg}")
            return Response({
                'success': False,
                'message': error_msg,
                'error': 'invalid_reference'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check warehouse capacity
        warehouse_commodity = WarehouseCommodity.objects.get(
            warehouse=warehouse,
            commodity=commodity
        )
        
        if not warehouse_commodity.can_add_quantity(data['quantity']):
            available_capacity = warehouse_commodity.get_available_capacity()
            error_msg = (
                f"Insufficient warehouse capacity. Available: {available_capacity} "
                f"{commodity.unit_of_measurement}, Requested: {data['quantity']}"
            )
            print(f"Validation Error: {error_msg}")
            return Response({
                'success': False,
                'message': error_msg,
                'available_capacity': float(available_capacity),
                'requested_quantity': float(data['quantity']),
                'unit': commodity.unit_of_measurement,
                'error': 'insufficient_capacity'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Process payment with the actual cost_charged amount
        print(f"Processing payment for amount: {cost_charged}")
        payment_result = process_payment(cost_charged, phone_number)
        
        if not payment_result['success']:
            print(f"Payment failed: {payment_result['message']}")
            
            # Return different status codes based on error type
            if payment_result['error_code'] in ['NETWORK_ERROR', 'TIMEOUT_ERROR']:
                response_status = status.HTTP_503_SERVICE_UNAVAILABLE
            elif payment_result['error_code'] in ['INVALID_AMOUNT', 'INVALID_PHONE']:
                response_status = status.HTTP_400_BAD_REQUEST
            else:
                response_status = status.HTTP_402_PAYMENT_REQUIRED
            
            return Response({
                'success': False,
                'message': payment_result['message'],
                'error': payment_result['error_code'],
                'payment_details': payment_result.get('data'),
                'technical_error': payment_result.get('technical_error')
            }, status=response_status)
        
        print("Payment successful or pending:", payment_result)
        
        # Set payment status based on the payment result
        payment_status = payment_result.get('payment_status', 'pending')
        
        # Set is_paid based on payment status
        # For 'completed' payments, set is_paid=True
        # For 'pending' payments, set is_paid=False but still create the order
        data['is_paid'] = (payment_status == 'completed')
        
        # Store payment transaction ID if available
        if payment_result.get('transaction_id'):
            data['payment_transaction_id'] = payment_result['transaction_id']
        
        # All validations passed - proceed with order creation
        print(f"All validations passed. Creating order with payment status: {payment_status}")
        
        with transaction.atomic():
            # Add user to the data
            data['user'] = request.user.id
            
            serializer = OrderSerializer(data=data, context={'request': request})
            
            if serializer.is_valid():
                order = serializer.save()
                
                print(f"Order created successfully. ID: {order.id}")
                print("Order details:", {
                    'id': order.id,
                    'origin': order.origin,
                    'warehouse': order.warehouse.location,
                    'commodity': order.commodity.name,
                    'quantity': float(order.quantity),
                    'cost_charged': float(order.cost_charged),
                    'status': order.status,
                    'phone_number': order.phone_number,
                    'is_paid': order.is_paid,
                    'payment_status': payment_status,
                    'created_at': order.created_at.isoformat()
                })
                
                response_serializer = OrderSerializer(order, context={'request': request})
                
                # Customize response message based on payment status
                if payment_status == 'completed':
                    success_message = 'Order created successfully with confirmed payment'
                elif payment_status == 'pending':
                    success_message = 'Order created successfully. Payment is pending confirmation.'
                else:
                    success_message = 'Order created successfully'
                
                return Response({
                    'success': True,
                    'message': success_message,
                    'data': response_serializer.data,
                    'payment_status': payment_status,
                    'payment_details': payment_result.get('data')
                }, status=status.HTTP_201_CREATED)
            else:
                error_msg = "Invalid order data"
                print(f"Serializer Errors: {serializer.errors}")
                return Response({
                    'success': False,
                    'message': error_msg,
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
    except Exception as e:
        error_msg = f"Unexpected error creating order: {str(e)}"
        print(f"ERROR: {error_msg}")
        print(traceback.format_exc())  # Print full traceback for debugging
        
        return Response({
            'success': False,
            'message': 'An unexpected error occurred while creating the order',
            'error': str(e),
            'error_type': type(e).__name__
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        
              

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_order_by_id(request, order_id):
    """Get order by ID"""
    try:
        order = get_object_or_404(Order, id=order_id)
        serializer = OrderSerializer(order, context={'request': request})
        
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error retrieving order: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_all_orders(request):
    """Get all orders"""
    try:
        queryset = Order.objects.select_related(
            'warehouse', 'commodity', 'category', 'user', 'inventory_movement'
        ).all()
        
        serializer = OrderSerializer(queryset, many=True, context={'request': request})
        print(f"Retrieved {len(serializer.data)} orders")
        if not serializer.data:
            return Response({
                'success': True,
                'message': 'No orders found',
                'data': []
            }, status=status.HTTP_200_OK)
        print("Order data:", serializer.data[:5])  # Print first 5 orders for debugging
        # Return all orders with detailed information
        
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error retrieving orders: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_user_orders(request):
    """Get all orders created by the logged-in user"""
    try:
        queryset = Order.objects.select_related(
            'warehouse', 'commodity', 'category', 'inventory_movement'
        ).filter(user=request.user)
        
        serializer = OrderSerializer(queryset, many=True, context={'request': request})
        
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error retrieving user orders: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def update_order(request, order_id):
    """Update an order (only for pending orders)"""
    try:
        order = get_object_or_404(Order, id=order_id)
        
        # Check if user owns the order or has admin privileges
        if order.user != request.user and not request.user.is_staff:
            return Response({
                'success': False,
                'message': 'You do not have permission to update this order'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = OrderUpdateSerializer(order, data=request.data, partial=True)
        
        if serializer.is_valid():
            with transaction.atomic():
                updated_order = serializer.save()
                
                # Return updated order with all details
                response_serializer = OrderSerializer(updated_order, context={'request': request})
                
                return Response({
                    'success': True,
                    'message': 'Order updated successfully',
                    'data': response_serializer.data
                }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'message': 'Invalid data provided',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error updating order: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_order(request, order_id):
    """Delete an order (only for pending orders)"""
    try:
        order = get_object_or_404(Order, id=order_id)
        
        # Check if user owns the order or has admin privileges
        if order.user != request.user and not request.user.is_staff:
            return Response({
                'success': False,
                'message': 'You do not have permission to delete this order'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Only allow deletion of pending orders
        if order.status != 'pending':
            return Response({
                'success': False,
                'message': 'Only pending orders can be deleted'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        order.delete()
        
        return Response({
            'success': True,
            'message': 'Order deleted successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error deleting order: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def confirm_order(request, order_id):
    """Confirm an order (admin/staff only)"""
    try:
        # Check if user has admin privileges
        if not request.user.is_staff:
            return Response({
                'success': False,
                'message': 'Only staff members can confirm orders'
            }, status=status.HTTP_403_FORBIDDEN)
        
        order = get_object_or_404(Order, id=order_id)
        
        with transaction.atomic():
            order.confirm_order()
            
            # Return updated order with all details
            serializer = OrderSerializer(order, context={'request': request})
            
            return Response({
                'success': True,
                'message': 'Order confirmed successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
    except DjangoValidationError as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error confirming order: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def reject_order(request, order_id):
    """Reject an order (admin/staff only)"""
    try:
        # Check if user has admin privileges
        if not request.user.is_staff:
            return Response({
                'success': False,
                'message': 'Only staff members can reject orders'
            }, status=status.HTTP_403_FORBIDDEN)
        
        order = get_object_or_404(Order, id=order_id)
        
        serializer = OrderActionSerializer(data=request.data)
        if serializer.is_valid():
            reason = serializer.validated_data.get('reason', '')
            
            with transaction.atomic():
                order.reject_order(reason)
                
                # Return updated order with all details
                response_serializer = OrderSerializer(order, context={'request': request})
                
                return Response({
                    'success': True,
                    'message': 'Order rejected successfully',
                    'data': response_serializer.data
                }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'message': 'Invalid data provided',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except DjangoValidationError as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error rejecting order: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        
        
        
        
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import Order
from .serializers import OrderSerializer

@api_view(['POST'])
@permission_classes([AllowAny])
def export_order(request, order_id):
    """Mark an order as exported"""
    try:
        order = Order.objects.get(id=order_id)
        
        # Check if user has permission to export orders
        # if not request.user.is_staff:
        #     return Response(
        #         {"detail": "You do not have permission to perform this action."},
        #         status=status.HTTP_403_FORBIDDEN
        #     )
        
        # Check if order can be exported
        if order.status != 'confirmed' or order.availability_status != 'imported':
            return Response(
                {"detail": "Only confirmed and imported orders can be exported"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Export the order
        try:
            order.export_order()
            return Response(
                {"detail": "Order successfully exported", "order": OrderSerializer(order).data},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Order.DoesNotExist:
        return Response(
            {"detail": "Order not found"},
            status=status.HTTP_404_NOT_FOUND
        )
        
        
        
        
        
        
        
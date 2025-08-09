# views.py - Create this file or add to existing views

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from .models import OrderDelivery, Driver
from .serializers import OrderDeliverySerializer, OrderDeliveryCreateUpdateSerializer
from orderApp.models import Order
from userApp.models import CustomUser

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_delivery(request):
    """Create a new delivery"""
    try:
        print(f"Creating delivery - User: {request.user}, Data: {request.data}")
        
        serializer = OrderDeliveryCreateUpdateSerializer(data=request.data)
        if serializer.is_valid():
            delivery = serializer.save(created_by=request.user)
            print(f"Delivery created successfully - ID: {delivery.id}")
            
            # Return detailed delivery info
            response_serializer = OrderDeliverySerializer(delivery)
            return Response({
                'success': True,
                'message': 'Delivery created successfully',
                'data': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        else:
            print(f"Validation errors: {serializer.errors}")
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except ValidationError as e:
        print(f"Validation error in create_delivery: {str(e)}")
        return Response({
            'success': False,
            'message': 'Validation error',
            'errors': {'detail': str(e)}
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        print(f"Unexpected error in create_delivery: {str(e)}")
        return Response({
            'success': False,
            'message': 'An unexpected error occurred',
            'errors': {'detail': str(e)}
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_deliveries(request):
    """Get all deliveries"""
    try:
        print(f"Fetching all deliveries - User: {request.user.phone_number}")
        
        deliveries = OrderDelivery.objects.all()
        serializer = OrderDeliverySerializer(deliveries, many=True)
        
        print(f"Found {len(deliveries)} deliveries")
        return Response({
            'success': True,
            'message': f'Found {len(deliveries)} deliveries',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error in get_all_deliveries: {str(e)}")
        return Response({
            'success': False,
            'message': 'An error occurred while fetching deliveries',
            'errors': {'detail': str(e)}
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_delivery_by_id(request, delivery_id):
    """Get delivery by ID"""
    try:
        print(f"Fetching delivery by ID: {delivery_id} - User: {request.user.phone_number}")
        
        delivery = get_object_or_404(OrderDelivery, id=delivery_id)
        serializer = OrderDeliverySerializer(delivery)
        
        print(f"Delivery found - ID: {delivery.id}")
        return Response({
            'success': True,
            'message': 'Delivery found',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error in get_delivery_by_id: {str(e)}")
        return Response({
            'success': False,
            'message': 'Delivery not found',
            'errors': {'detail': str(e)}
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_deliveries_created_by_user(request):
    """Get all deliveries created by logged-in user"""
    try:
        print(f"Fetching deliveries created by user: {request.user.phone_number}")
        
        deliveries = OrderDelivery.objects.filter(created_by=request.user)
        serializer = OrderDeliverySerializer(deliveries, many=True)
        
        print(f"Found {len(deliveries)} deliveries created by user")
        return Response({
            'success': True,
            'message': f'Found {len(deliveries)} deliveries created by you',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error in get_deliveries_created_by_user: {str(e)}")
        return Response({
            'success': False,
            'message': 'An error occurred while fetching your deliveries',
            'errors': {'detail': str(e)}
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_deliveries_assigned_to_driver(request):
    """Get all deliveries assigned to logged-in driver"""
    try:
        print(f"Fetching deliveries assigned to driver user: {request.user.phone_number}")
        
        # Check if user is a driver
        try:
            driver = Driver.objects.get(user=request.user)
        except Driver.DoesNotExist:
            print(f"User {request.user.phone_number} is not a driver")
            return Response({
                'success': False,
                'message': 'You are not registered as a driver',
                'errors': {'detail': 'User is not a driver'}
            }, status=status.HTTP_403_FORBIDDEN)
        
        deliveries = OrderDelivery.objects.filter(driver=driver)
        serializer = OrderDeliverySerializer(deliveries, many=True)
        
        print(f"Found {len(deliveries)} deliveries assigned to driver")
        return Response({
            'success': True,
            'message': f'Found {len(deliveries)} deliveries assigned to you',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error in get_deliveries_assigned_to_driver: {str(e)}")
        return Response({
            'success': False,
            'message': 'An error occurred while fetching your assigned deliveries',
            'errors': {'detail': str(e)}
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_delivery(request, delivery_id):
    """Update a delivery"""
    try:
        print(f"Updating delivery ID: {delivery_id} - User: {request.user.phone_number}, Data: {request.data}")
        
        delivery = get_object_or_404(OrderDelivery, id=delivery_id)
        
        # Use partial update for PATCH
        partial = request.method == 'PATCH'
        serializer = OrderDeliveryCreateUpdateSerializer(delivery, data=request.data, partial=partial)
        
        if serializer.is_valid():
            updated_delivery = serializer.save()
            print(f"Delivery updated successfully - ID: {updated_delivery.id}")
            
            # Return detailed delivery info
            response_serializer = OrderDeliverySerializer(updated_delivery)
            return Response({
                'success': True,
                'message': 'Delivery updated successfully',
                'data': response_serializer.data
            }, status=status.HTTP_200_OK)
        else:
            print(f"Validation errors in update: {serializer.errors}")
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except ValidationError as e:
        print(f"Validation error in update_delivery: {str(e)}")
        return Response({
            'success': False,
            'message': 'Validation error',
            'errors': {'detail': str(e)}
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        print(f"Error in update_delivery: {str(e)}")
        return Response({
            'success': False,
            'message': 'An error occurred while updating the delivery',
            'errors': {'detail': str(e)}
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_delivery(request, delivery_id):
    """Delete a delivery"""
    try:
        print(f"Deleting delivery ID: {delivery_id} - User: {request.user.phone_number}")
        
        delivery = get_object_or_404(OrderDelivery, id=delivery_id)
        
        # Optional: Add permission check if only creator can delete
        # if delivery.created_by != request.user:
        #     return Response({
        #         'success': False,
        #         'message': 'You can only delete deliveries you created'
        #     }, status=status.HTTP_403_FORBIDDEN)
        
        delivery_id_copy = delivery.id
        delivery.delete()
        
        print(f"Delivery deleted successfully - ID: {delivery_id_copy}")
        return Response({
            'success': True,
            'message': 'Delivery deleted successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error in delete_delivery: {str(e)}")
        return Response({
            'success': False,
            'message': 'An error occurred while deleting the delivery',
            'errors': {'detail': str(e)}
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_deliveries_assigned_to_customer(request):
    """Get all deliveries"""
    try:
        
        print(f"Fetching all deliveries - User: {request.user.phone_number}")
        # Assuming the customer is the user making the request
        if not request.user:
            return Response({
                'success': False,
                'message': 'You must be logged in to view deliveries',
                'errors': {'detail': 'Authentication required'}
            }, status=status.HTTP_401_UNAUTHORIZED)
        # Get the order for the customer
        print(f"Fetching order for customer: {request.user.phone_number}")
        order = Order.objects.filter(user=request.user).first()
        if not order:
            print(f"No orders found for customer: {request.user.phone_number}")
            return Response({
                'success': False,
                'message': 'No orders found for this customer',
                'errors': {'detail': 'No orders found'}
            }, status=status.HTTP_404_NOT_FOUND)
            
        # Get all deliveries for the order
        print(f"Fetching deliveries for order ID: {order.id}")
        deliveries = OrderDelivery.objects.filter(order=order)
        if not deliveries:
            print(f"No deliveries found for customer: {request.user.phone_number}")
            return Response({
                'success': False,
                'message': 'No deliveries found for this customer',
                'errors': {'detail': 'No deliveries found'}
            }, status=status.HTTP_404_NOT_FOUND)
        serializer = OrderDeliverySerializer(deliveries, many=True)
        
        print(f"Found {len(deliveries)} deliveries")
        return Response({
            'success': True,
            'message': f'Found {len(deliveries)} deliveries',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error in get_all_deliveries: {str(e)}")
        return Response({
            'success': False,
            'message': 'An error occurred while fetching deliveries',
            'errors': {'detail': str(e)}
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




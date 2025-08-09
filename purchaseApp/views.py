# purchaseApp/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from paypack.client import HttpClient
from paypack.transactions import Transaction

from .models import Purchase, PurchasePayment
from sellsApp.models import Sell
from .serializers import (
    PurchaseSerializer, PurchaseCreateSerializer, PurchaseUpdateSerializer,
    PurchasePaymentSerializer, PaymentCreateSerializer, PurchaseStatusUpdateSerializer
)

# PayPack configuration
CLIENT_ID = "your_client_id_here"  # Replace with actual client ID
CLIENT_SECRET = "your_client_secret_here"  # Replace with actual client secret


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def purchase_sell(request):
    """
    Create a purchase for a sell by a buyer.
    """
    try:
        # Validate user is a buyer
        if request.user.role != 'buyer':
            print(f"Error: Non-buyer user {request.user.phone_number} tried to make purchase")
            return Response(
                {'error': 'Only buyers can make purchases'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate request data
        serializer = PurchaseCreateSerializer(data=request.data)
        if not serializer.is_valid():
            print(f"Error: Invalid purchase data - {serializer.errors}")
            return Response(
                {'error': 'Invalid data provided', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        validated_data = serializer.validated_data
        
        with transaction.atomic():
            # Get the sell
            sell = get_object_or_404(Sell, id=validated_data['sell_id'])
            
            # Double-check sell availability
            if sell.sell_status != 'posted':
                print(f"Error: Sell {sell.id} is no longer available - status: {sell.sell_status}")
                return Response(
                    {'error': 'This sell is no longer available for purchase'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if sell already has a purchase
            if hasattr(sell, 'purchase'):
                print(f"Error: Sell {sell.id} already has a purchase")
                return Response(
                    {'error': 'This sell has already been purchased'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create the purchase
            purchase = Purchase.objects.create(
                buyer=request.user,
                sell=sell,
                quantity_purchased=sell.quantity_sold,
                unit_price=sell.unit_price,
                delivery_address=validated_data['delivery_address'],
                delivery_notes=validated_data.get('delivery_notes', ''),
                notes=validated_data.get('notes', '')
            )
            
            print(f"Success: Purchase {purchase.id} created by buyer {request.user.phone_number}")
            
            # Serialize and return the purchase
            purchase_serializer = PurchaseSerializer(purchase)
            return Response(
                {
                    'message': 'Purchase created successfully',
                    'purchase': purchase_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
    
    except Sell.DoesNotExist:
        print(f"Error: Sell with ID {request.data.get('sell_id')} not found")
        return Response(
            {'error': 'Sell not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        print(f"Error creating purchase: {str(e)}")
        return Response(
            {'error': 'An error occurred while creating the purchase. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_purchases(request):
    """
    Get all purchases in the system (admin view).
    """
    try:
        # Check if user has permission to view all purchases
        if request.user.role not in ['admin', 'minagri_officer']:
            print(f"Error: User {request.user.phone_number} tried to access all purchases without permission")
            return Response(
                {'error': 'You do not have permission to view all purchases'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        purchases = Purchase.objects.all().select_related('buyer', 'sell__farmer', 'sell__harvest_stock__harvest')
        serializer = PurchaseSerializer(purchases, many=True)
        
        print(f"Success: Retrieved {purchases.count()} purchases for admin user {request.user.phone_number}")
        
        return Response(
            {
                'message': 'Purchases retrieved successfully',
                'count': purchases.count(),
                'purchases': serializer.data
            },
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        print(f"Error retrieving all purchases: {str(e)}")
        return Response(
            {'error': 'An error occurred while retrieving purchases. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_purchases(request):
    """
    Get all purchases made by the logged-in buyer.
    """
    try:
        # Validate user is a buyer
        if request.user.role != 'buyer':
            print(f"Error: Non-buyer user {request.user.phone_number} tried to access buyer purchases")
            return Response(
                {'error': 'Only buyers can view their purchases'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        purchases = Purchase.objects.filter(buyer=request.user).select_related(
            'sell__farmer', 'sell__harvest_stock__harvest'
        ).prefetch_related('payments')
        
        serializer = PurchaseSerializer(purchases, many=True)
        
        print(f"Success: Retrieved {purchases.count()} purchases for buyer {request.user.phone_number}")
        
        return Response(
            {
                'message': 'Your purchases retrieved successfully',
                'count': purchases.count(),
                'purchases': serializer.data
            },
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        print(f"Error retrieving user purchases: {str(e)}")
        return Response(
            {'error': 'An error occurred while retrieving your purchases. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_purchase_status(request, purchase_id):
    """
    Update purchase status (for farmers and admins).
    """
    try:
        purchase = get_object_or_404(Purchase, id=purchase_id)
        
        # Check permissions
        if request.user.role not in ['admin', 'minagri_officer']:
            # Farmers can only update their own sells' purchases
            if request.user.role == 'farmer' and purchase.sell.farmer != request.user:
                print(f"Error: Farmer {request.user.phone_number} tried to update purchase {purchase_id} not belonging to them")
                return Response(
                    {'error': 'You can only update purchases for your own sells'},
                    status=status.HTTP_403_FORBIDDEN
                )
            elif request.user.role == 'buyer' and purchase.buyer != request.user:
                print(f"Error: Buyer {request.user.phone_number} tried to update purchase {purchase_id} not belonging to them")
                return Response(
                    {'error': 'You can only update your own purchases'},
                    status=status.HTTP_403_FORBIDDEN
                )
            elif request.user.role not in ['farmer', 'buyer']:
                return Response(
                    {'error': 'You do not have permission to update purchase status'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Validate status update
        serializer = PurchaseStatusUpdateSerializer(
            data=request.data,
            context={'purchase': purchase}
        )
        if not serializer.is_valid():
            print(f"Error: Invalid status update data for purchase {purchase_id} - {serializer.errors}")
            return Response(
                {'error': 'Invalid data provided', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        validated_data = serializer.validated_data
        old_status = purchase.purchase_status
        
        with transaction.atomic():
            # Update purchase
            purchase.purchase_status = validated_data['status']
            if validated_data.get('notes'):
                purchase.notes = validated_data['notes']
            
            # Set actual delivery date if marking as delivered
            if validated_data['status'] == 'delivered':
                purchase.actual_delivery_date = timezone.now().date()
                # Also update the sell status to completed
                purchase.sell.sell_status = 'completed'
                purchase.sell.save()
            
            purchase.save()
        
        print(f"Success: Purchase {purchase_id} status updated from {old_status} to {validated_data['status']}")
        
        purchase_serializer = PurchaseSerializer(purchase)
        return Response(
            {
                'message': 'Purchase status updated successfully',
                'purchase': purchase_serializer.data
            },
            status=status.HTTP_200_OK
        )
    
    except Purchase.DoesNotExist:
        print(f"Error: Purchase with ID {purchase_id} not found")
        return Response(
            {'error': 'Purchase not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        print(f"Error updating purchase status: {str(e)}")
        return Response(
            {'error': 'An error occurred while updating purchase status. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def make_payment(request):
    """
    Make a payment for a purchase using PayPack.
    """
    try:
        # Validate user is a buyer
        if request.user.role != 'buyer':
            print(f"Error: Non-buyer user {request.user.phone_number} tried to make payment")
            return Response(
                {'error': 'Only buyers can make payments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate payment data
        serializer = PaymentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            print(f"Error: Invalid payment data - {serializer.errors}")
            return Response(
                {'error': 'Invalid data provided', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        validated_data = serializer.validated_data
        
        # Get the purchase
        purchase = get_object_or_404(Purchase, id=validated_data['purchase_id'])
        
        # Validate buyer owns the purchase
        if purchase.buyer != request.user:
            print(f"Error: Buyer {request.user.phone_number} tried to pay for purchase {purchase.id} not belonging to them")
            return Response(
                {'error': 'You can only make payments for your own purchases'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if purchase can accept payments
        if not purchase.can_make_payment:
            print(f"Error: Purchase {purchase.id} cannot accept more payments - status: {purchase.purchase_status}")
            return Response(
                {'error': 'This purchase cannot accept more payments'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check payment amount doesn't exceed remaining balance
        if validated_data['amount'] > purchase.remaining_balance:
            print(f"Error: Payment amount {validated_data['amount']} exceeds remaining balance {purchase.remaining_balance}")
            return Response(
                {'error': f'Payment amount cannot exceed remaining balance of {purchase.remaining_balance}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # Create payment record first
            payment = PurchasePayment.objects.create(
                purchase=purchase,
                amount=validated_data['amount'],
                payment_method=validated_data.get('payment_method', 'paypack'),
                phone_number=validated_data['phone_number'],
                notes=validated_data.get('notes', ''),
                status='pending'
            )
            
            # Process PayPack payment if payment method is paypack
            if validated_data.get('payment_method', 'paypack') == 'paypack':
                try:
                    # Initialize PayPack client
                    client = HttpClient(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
                    
                    # Create transaction
                    transaction_obj = Transaction()
                    cashin_response = transaction_obj.cashin(
                        amount=int(validated_data['amount']),  # PayPack expects integer
                        phone_number=validated_data['phone_number']
                    )
                    
                    print(f"PayPack response for payment {payment.id}: {cashin_response}")
                    
                    # Update payment with PayPack response
                    if cashin_response and 'ref' in cashin_response:
                        payment.paypack_ref = cashin_response.get('ref')
                        payment.paypack_status = cashin_response.get('status', 'unknown')
                        payment.reference_number = cashin_response.get('ref')
                        
                        # If PayPack returns pending status, save payment as pending
                        if cashin_response.get('status') == 'pending':
                            payment.status = 'pending'
                            print(f"Success: PayPack payment {payment.id} created with ref {payment.paypack_ref}")
                        else:
                            payment.status = 'failed'
                            payment.failure_reason = f"Unexpected PayPack status: {cashin_response.get('status')}"
                            print(f"Warning: PayPack returned unexpected status: {cashin_response.get('status')}")
                    else:
                        payment.status = 'failed'
                        payment.failure_reason = 'Invalid response from PayPack'
                        print(f"Error: Invalid PayPack response for payment {payment.id}")
                    
                    payment.save()
                    
                except Exception as paypack_error:
                    print(f"PayPack error for payment {payment.id}: {str(paypack_error)}")
                    payment.status = 'failed'
                    payment.failure_reason = f'PayPack error: {str(paypack_error)}'
                    payment.save()
                    
                    return Response(
                        {'error': 'Payment processing failed. Please try again later.'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            else:
                # For non-PayPack payments, mark as completed immediately
                payment.status = 'completed'
                payment.completed_date = timezone.now()
                payment.save()
        
        # Serialize and return the payment
        payment_serializer = PurchasePaymentSerializer(payment)
        return Response(
            {
                'message': 'Payment processed successfully',
                'payment': payment_serializer.data
            },
            status=status.HTTP_201_CREATED
        )
    
    except Purchase.DoesNotExist:
        print(f"Error: Purchase with ID {request.data.get('purchase_id')} not found")
        return Response(
            {'error': 'Purchase not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        print(f"Error processing payment: {str(e)}")
        return Response(
            {'error': 'An error occurred while processing payment. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_purchase(request, purchase_id):
    """
    Update purchase details (delivery address, notes, etc.).
    """
    try:
        purchase = get_object_or_404(Purchase, id=purchase_id)
        
        # Validate buyer owns the purchase
        if purchase.buyer != request.user and request.user.role not in ['admin', 'minagri_officer']:
            print(f"Error: User {request.user.phone_number} tried to update purchase {purchase_id} without permission")
            return Response(
                {'error': 'You can only update your own purchases'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate update data
        serializer = PurchaseUpdateSerializer(purchase, data=request.data, partial=True)
        if not serializer.is_valid():
            print(f"Error: Invalid update data for purchase {purchase_id} - {serializer.errors}")
            return Response(
                {'error': 'Invalid data provided', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Save updates
        updated_purchase = serializer.save()
        
        print(f"Success: Purchase {purchase_id} updated by user {request.user.phone_number}")
        
        # Serialize and return updated purchase
        purchase_serializer = PurchaseSerializer(updated_purchase)
        return Response(
            {
                'message': 'Purchase updated successfully',
                'purchase': purchase_serializer.data
            },
            status=status.HTTP_200_OK
        )
    
    except Purchase.DoesNotExist:
        print(f"Error: Purchase with ID {purchase_id} not found")
        return Response(
            {'error': 'Purchase not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        print(f"Error updating purchase: {str(e)}")
        return Response(
            {'error': 'An error occurred while updating purchase. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_purchase(request, purchase_id):
    """
    Delete a purchase (only if not fully paid).
    """
    try:
        purchase = get_object_or_404(Purchase, id=purchase_id)
        
        # Check permissions
        if request.user.role not in ['admin', 'minagri_officer']:
            if purchase.buyer != request.user:
                print(f"Error: User {request.user.phone_number} tried to delete purchase {purchase_id} without permission")
                return Response(
                    {'error': 'You can only delete your own purchases'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Validate purchase can be deleted
        if purchase.purchase_status in ['fully_paid', 'delivered']:
            print(f"Error: Attempted to delete fully paid/delivered purchase {purchase_id}")
            return Response(
                {'error': 'Cannot delete fully paid or delivered purchases'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if any payments have been made
        if purchase.amount_paid > 0:
            print(f"Error: Attempted to delete purchase {purchase_id} with payments made")
            return Response(
                {'error': 'Cannot delete purchases with payments made. Please contact admin for refund.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # Reset the sell status to posted
            sell = purchase.sell
            sell.sell_status = 'posted'
            sell.buyer = None
            sell.amount_paid = Decimal('0.00')
            sell.payment_status = 'unpaid'
            sell.delivery_address = ''
            sell.purchased_date = None
            sell.payment_completed_date = None
            sell.delivery_date = None
            sell.save()
            
            # Delete the purchase
            purchase_id_copy = purchase.id
            purchase.delete()
            
            print(f"Success: Purchase {purchase_id_copy} deleted and sell {sell.id} reset to available")
        
        return Response(
            {'message': 'Purchase deleted successfully'},
            status=status.HTTP_200_OK
        )
    
    except Purchase.DoesNotExist:
        print(f"Error: Purchase with ID {purchase_id} not found")
        return Response(
            {'error': 'Purchase not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        print(f"Error deleting purchase: {str(e)}")
        return Response(
            {'error': 'An error occurred while deleting purchase. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_farmer_sell_purchases(request):
    """
    Get all purchases for sells created by the logged-in farmer.
    """
    try:
        # Validate user is a farmer
        if request.user.role != 'farmer':
            print(f"Error: Non-farmer user {request.user.phone_number} tried to access farmer sell purchases")
            return Response(
                {'error': 'Only farmers can view purchases for their sells'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get purchases for sells created by this farmer
        purchases = Purchase.objects.filter(sell__farmer=request.user).select_related(
            'buyer', 'sell', 'sell__harvest_stock__harvest'
        ).prefetch_related('payments')
        
        serializer = PurchaseSerializer(purchases, many=True)
        
        print(f"Success: Retrieved {purchases.count()} purchases for farmer {request.user.phone_number}")
        
        return Response(
            {
                'message': 'Purchases for your sells retrieved successfully',
                'count': purchases.count(),
                'purchases': serializer.data
            },
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        print(f"Error retrieving farmer sell purchases: {str(e)}")
        return Response(
            {'error': 'An error occurred while retrieving purchases. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_purchase_payments(request, purchase_id):
    """
    Get all payments for a specific purchase.
    """
    try:
        purchase = get_object_or_404(Purchase, id=purchase_id)
        
        # Check permissions
        if request.user.role not in ['admin', 'minagri_officer']:
            # Buyers can view their own purchase payments
            # Farmers can view payments for their sell purchases
            if (purchase.buyer != request.user and 
                purchase.sell.farmer != request.user):
                print(f"Error: User {request.user.phone_number} tried to access payments for purchase {purchase_id} without permission")
                return Response(
                    {'error': 'You do not have permission to view these payments'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        payments = purchase.payments.all()
        serializer = PurchasePaymentSerializer(payments, many=True)
        
        print(f"Success: Retrieved {payments.count()} payments for purchase {purchase_id}")
        
        return Response(
            {
                'message': 'Payments retrieved successfully',
                'count': payments.count(),
                'payments': serializer.data,
                'purchase_summary': {
                    'total_amount': purchase.total_amount,
                    'amount_paid': purchase.amount_paid,
                    'remaining_balance': purchase.remaining_balance,
                    'payment_progress': purchase.payment_progress
                }
            },
            status=status.HTTP_200_OK
        )
    
    except Purchase.DoesNotExist:
        print(f"Error: Purchase with ID {purchase_id} not found")
        return Response(
            {'error': 'Purchase not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        print(f"Error retrieving purchase payments: {str(e)}")
        return Response(
            {'error': 'An error occurred while retrieving payments. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirm_payment(request, payment_id):
    """
    Confirm a pending payment (webhook endpoint or manual confirmation).
    """
    try:
        payment = get_object_or_404(PurchasePayment, id=payment_id)
        
        # Check permissions - only admins or the purchase buyer can confirm
        if request.user.role not in ['admin', 'minagri_officer']:
            if payment.purchase.buyer != request.user:
                print(f"Error: User {request.user.phone_number} tried to confirm payment {payment_id} without permission")
                return Response(
                    {'error': 'You do not have permission to confirm this payment'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Validate payment is in pending status
        if payment.status != 'pending':
            print(f"Error: Attempted to confirm payment {payment_id} with status {payment.status}")
            return Response(
                {'error': f'Payment is not in pending status. Current status: {payment.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # Update payment status
            payment.status = 'completed'
            payment.completed_date = timezone.now()
            payment.save()
            
            print(f"Success: Payment {payment_id} confirmed and marked as completed")
        
        # Serialize and return updated payment
        payment_serializer = PurchasePaymentSerializer(payment)
        return Response(
            {
                'message': 'Payment confirmed successfully',
                'payment': payment_serializer.data
            },
            status=status.HTTP_200_OK
        )
    
    except PurchasePayment.DoesNotExist:
        print(f"Error: Payment with ID {payment_id} not found")
        return Response(
            {'error': 'Payment not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        print(f"Error confirming payment: {str(e)}")
        return Response(
            {'error': 'An error occurred while confirming payment. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from .models import Sell, SellPayment
from .serializers import (
    SellSerializer,
    SellCreateSerializer,
    SellUpdateSerializer,
    SellPurchaseSerializer,
    SellListSerializer,
    AvailableSellSerializer,
    PaymentCreateSerializer,
    SellPaymentSerializer,
    DeliveryUpdateSerializer
)
from stockApp.models import HarvestStock
from userApp.models import CustomUser


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_sell_post(request):
    """Create a new sell post for farmers (no buyer initially)."""
    try:
        # Ensure only farmers can create sell posts
        if request.user.role != 'farmer':
            return Response(
                {'error': 'Only farmers can create sell posts'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = SellCreateSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    sell = serializer.save(
                        farmer=request.user,
                        sell_status='posted'  # Default status for new posts
                    )
                    
                    # Return full sell data
                    response_serializer = SellSerializer(sell)
                    return Response(
                        {
                            'message': 'Sell post created successfully',
                            'sell': response_serializer.data
                        },
                        status=status.HTTP_201_CREATED
                    )
            except Exception as e:
                print(f"Error creating sell post: {str(e)}")
                return Response(
                    {'error': 'Failed to create sell post. Please try again.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Exception as e:
        print(f"Unexpected error in create_sell_post: {str(e)}")
        return Response(
            {'error': 'An unexpected error occurred'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_available_sells(request):
    """Get all available sells for buyers to purchase."""
    try:
        # Only buyers should access this endpoint primarily, but allow others to view
        sells = Sell.objects.filter(sell_status='posted').select_related(
            'farmer', 'harvest_stock__harvest'
        )
        
        serializer = AvailableSellSerializer(sells, many=True)
        
        return Response(
            {
                'count': sells.count(),
                'available_sells': serializer.data
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        print(f"Error retrieving available sells: {str(e)}")
        return Response(
            {'error': 'Failed to retrieve available sells'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def purchase_sell(request, sell_id):
    """Allow buyers to purchase a posted sell."""
    try:
        # Ensure only buyers can purchase
        if request.user.role != 'buyer':
            return Response(
                {'error': 'Only buyers can purchase items'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        sell = get_object_or_404(Sell, id=sell_id)
        
        # Check if sell is available for purchase
        if sell.sell_status != 'posted':
            return Response(
                {'error': 'This item is no longer available for purchase'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if buyer is trying to purchase their own post (shouldn't happen but safety check)
        if sell.farmer == request.user:
            return Response(
                {'error': 'You cannot purchase your own items'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = SellPurchaseSerializer(sell, data=request.data, partial=True)
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    # Use the model method to handle purchase
                    delivery_address = serializer.validated_data['delivery_address']
                    sell.purchase_by_buyer(request.user, delivery_address)
                    
                    # Return updated sell data
                    response_serializer = SellSerializer(sell)
                    return Response(
                        {
                            'message': 'Item purchased successfully',
                            'purchase': response_serializer.data
                        },
                        status=status.HTTP_200_OK
                    )
            except Exception as e:
                print(f"Error purchasing sell {sell_id}: {str(e)}")
                return Response(
                    {'error': 'Failed to purchase item. Please try again.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Sell.DoesNotExist:
        return Response(
            {'error': 'Sell not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        print(f"Unexpected error purchasing sell {sell_id}: {str(e)}")
        return Response(
            {'error': 'An unexpected error occurred'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_sells(request):
    """Get sells created by the logged-in farmer."""
    try:
        # Ensure only farmers can access this endpoint
        if request.user.role != 'farmer':
            return Response(
                {'error': 'Only farmers can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        sells = Sell.objects.filter(farmer=request.user).select_related(
            'buyer', 'harvest_stock__harvest'
        )
        serializer = SellListSerializer(sells, many=True)
        
        return Response(
            {
                'count': sells.count(),
                'my_sells': serializer.data
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        print(f"Error retrieving user sells: {str(e)}")
        return Response(
            {'error': 'Failed to retrieve your sells'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_purchases(request):
    """Get purchases made by the logged-in buyer."""
    try:
        # Ensure only buyers can access this endpoint
        if request.user.role != 'buyer':
            return Response(
                {'error': 'Only buyers can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        purchases = Sell.objects.filter(buyer=request.user).select_related(
            'farmer', 'harvest_stock__harvest'
        )
        serializer = SellListSerializer(purchases, many=True)
        
        return Response(
            {
                'count': purchases.count(),
                'my_purchases': serializer.data
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        print(f"Error retrieving user purchases: {str(e)}")
        return Response(
            {'error': 'Failed to retrieve your purchases'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_sells(request):
    """Get all sells (admin/minagri officers) or filter by permissions."""
    try:
        # Only admin and minagri officers can see all sells
        if request.user.role not in ['admin', 'minagri_officer', 'client', 'customer', 'buyer', 'farmer']:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        sells = Sell.objects.all().select_related(
            'farmer', 'buyer', 'harvest_stock__harvest'
        )
        serializer = SellListSerializer(sells, many=True)
        
        return Response(
            {
                'count': sells.count(),
                'sells': serializer.data
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        print(f"Error retrieving all sells: {str(e)}")
        return Response(
            {'error': 'Failed to retrieve sells'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_sell_by_id(request, sell_id):
    """Get a specific sell by ID."""
    try:
        sell = get_object_or_404(Sell, id=sell_id)
        
        # Check permissions
        if request.user.role == 'farmer' and sell.farmer != request.user:
            return Response(
                {'error': 'You can only view your own sells'},
                status=status.HTTP_403_FORBIDDEN
            )
        elif request.user.role == 'buyer' and sell.buyer != request.user:
            # Buyers can view available items or their purchases
            if sell.sell_status not in ['posted'] and sell.buyer != request.user:
                return Response(
                    {'error': 'You can only view available items or your purchases'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        serializer = SellSerializer(sell)
        
        return Response(
            {'sell': serializer.data},
            status=status.HTTP_200_OK
        )
        
    except Sell.DoesNotExist:
        return Response(
            {'error': 'Sell not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        print(f"Error retrieving sell {sell_id}: {str(e)}")
        return Response(
            {'error': 'Failed to retrieve sell'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_sell(request, sell_id):
    """Update a specific sell."""
    try:
        sell = get_object_or_404(Sell, id=sell_id)
        
        # Check permissions - farmers can only update their own posted sells
        if request.user.role == 'farmer' and sell.farmer != request.user:
            return Response(
                {'error': 'You can only update your own sells'},
                status=status.HTTP_403_FORBIDDEN
            )
        elif request.user.role != 'farmer':
            return Response(
                {'error': 'Only farmers can update sell posts'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Only allow updating posted items
        if sell.sell_status != 'posted':
            return Response(
                {'error': 'Can only update posted items that haven\'t been purchased'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = SellUpdateSerializer(
            sell, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    updated_sell = serializer.save()
                    
                    # Return full sell data
                    response_serializer = SellSerializer(updated_sell)
                    return Response(
                        {
                            'message': 'Sell updated successfully',
                            'sell': response_serializer.data
                        },
                        status=status.HTTP_200_OK
                    )
            except Exception as e:
                print(f"Error updating sell {sell_id}: {str(e)}")
                return Response(
                    {'error': 'Failed to update sell. Please try again.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Sell.DoesNotExist:
        return Response(
            {'error': 'Sell not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        print(f"Unexpected error updating sell {sell_id}: {str(e)}")
        return Response(
            {'error': 'An unexpected error occurred'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_delivery_info(request, sell_id):
    """Update delivery information for purchased items."""
    try:
        sell = get_object_or_404(Sell, id=sell_id)
        
        # Check permissions - buyers can update delivery info for their purchases
        if request.user.role == 'buyer' and sell.buyer != request.user:
            return Response(
                {'error': 'You can only update delivery info for your purchases'},
                status=status.HTTP_403_FORBIDDEN
            )
        elif request.user.role == 'farmer' and sell.farmer != request.user:
            return Response(
                {'error': 'Farmers can only update delivery info for their sells'},
                status=status.HTTP_403_FORBIDDEN
            )
        elif request.user.role not in ['farmer', 'buyer', 'admin']:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = DeliveryUpdateSerializer(
            sell, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    updated_sell = serializer.save()
                    
                    # Return full sell data
                    response_serializer = SellSerializer(updated_sell)
                    return Response(
                        {
                            'message': 'Delivery information updated successfully',
                            'sell': response_serializer.data
                        },
                        status=status.HTTP_200_OK
                    )
            except Exception as e:
                print(f"Error updating delivery info for sell {sell_id}: {str(e)}")
                return Response(
                    {'error': 'Failed to update delivery information. Please try again.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Sell.DoesNotExist:
        return Response(
            {'error': 'Sell not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        print(f"Unexpected error updating delivery info for sell {sell_id}: {str(e)}")
        return Response(
            {'error': 'An unexpected error occurred'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_sell(request, sell_id):
    """Mark a sell as completed (farmer or admin only)."""
    try:
        sell = get_object_or_404(Sell, id=sell_id)
        
        # Check permissions
        if request.user.role == 'farmer' and sell.farmer != request.user:
            return Response(
                {'error': 'You can only complete your own sells'},
                status=status.HTTP_403_FORBIDDEN
            )
        elif request.user.role not in ['farmer', 'admin', 'minagri_officer']:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if sell can be completed
        if sell.sell_status != 'purchased':
            return Response(
                {'error': 'Only purchased items can be completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                sell.sell_status = 'completed'
                sell.save()  # This will trigger stock movement creation
                
                response_serializer = SellSerializer(sell)
                return Response(
                    {
                        'message': 'Sell completed successfully. Stock movement has been recorded.',
                        'sell': response_serializer.data
                    },
                    status=status.HTTP_200_OK
                )
        except Exception as e:
            print(f"Error completing sell {sell_id}: {str(e)}")
            return Response(
                {'error': 'Failed to complete sell. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Sell.DoesNotExist:
        return Response(
            {'error': 'Sell not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        print(f"Unexpected error completing sell {sell_id}: {str(e)}")
        return Response(
            {'error': 'An unexpected error occurred'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_sell(request, sell_id):
    """Delete a specific sell (only posted items)."""
    try:
        sell = get_object_or_404(Sell, id=sell_id)
        
        # Check permissions - farmers can only delete their own sells
        if request.user.role == 'farmer' and sell.farmer != request.user:
            return Response(
                {'error': 'You can only delete your own sells'},
                status=status.HTTP_403_FORBIDDEN
            )
        elif request.user.role not in ['farmer', 'admin']:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Don't allow deleting purchased/completed sells
        if sell.sell_status in ['purchased', 'completed']:
            return Response(
                {'error': 'Cannot delete purchased or completed sells'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if there are any payments
        if sell.payments.exists():
            return Response(
                {'error': 'Cannot delete sells with existing payments'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                sell_info = f"Sell #{sell.id} - {sell.quantity_sold}kg"
                sell.delete()
                
                return Response(
                    {'message': f'{sell_info} deleted successfully'},
                    status=status.HTTP_200_OK
                )
        except Exception as e:
            print(f"Error deleting sell {sell_id}: {str(e)}")
            return Response(
                {'error': 'Failed to delete sell. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Sell.DoesNotExist:
        return Response(
            {'error': 'Sell not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        print(f"Unexpected error deleting sell {sell_id}: {str(e)}")
        return Response(
            {'error': 'An unexpected error occurred'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment(request):
    """Create a payment for a sell."""
    try:
        serializer = PaymentCreateSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    payment = serializer.save()
                    
                    # Return payment data with updated sell info
                    response_serializer = SellPaymentSerializer(payment)
                    sell_serializer = SellSerializer(payment.sell)
                    
                    return Response(
                        {
                            'message': 'Payment recorded successfully',
                            'payment': response_serializer.data,
                            'sell': sell_serializer.data
                        },
                        status=status.HTTP_201_CREATED
                    )
            except Exception as e:
                print(f"Error creating payment: {str(e)}")
                return Response(
                    {'error': 'Failed to record payment. Please try again.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Exception as e:
        print(f"Unexpected error in create_payment: {str(e)}")
        return Response(
            {'error': 'An unexpected error occurred'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_payment_status(request, sell_id):
    """Update payment status when submitted amount equals total amount."""
    try:
        sell = get_object_or_404(Sell, id=sell_id)
        
        # Check permissions
        if request.user.role == 'buyer' and sell.buyer != request.user:
            return Response(
                {'error': 'You can only update payment for your purchases'},
                status=status.HTTP_403_FORBIDDEN
            )
        elif request.user.role == 'farmer' and sell.farmer != request.user:
            return Response(
                {'error': 'You can only update payment for your sells'},
                status=status.HTTP_403_FORBIDDEN
            )
        elif request.user.role not in ['farmer', 'buyer', 'admin', 'minagri_officer']:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get the submitted amount from request
        submitted_amount = request.data.get('amount_paid')
        if not submitted_amount:
            return Response(
                {'error': 'amount_paid is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            submitted_amount = Decimal(str(submitted_amount))
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid amount format'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if submitted amount equals total amount
        if submitted_amount == sell.total_amount:
            try:
                with transaction.atomic():
                    sell.amount_paid = submitted_amount
                    sell.payment_status = 'paid'
                    sell.update_payment_completion()  # This will set delivery date
                    sell.save()
                    
                    response_serializer = SellSerializer(sell)
                    return Response(
                        {
                            'message': 'Payment status updated to fully paid. Delivery date calculated.',
                            'sell': response_serializer.data
                        },
                        status=status.HTTP_200_OK
                    )
            except Exception as e:
                print(f"Error updating payment status for sell {sell_id}: {str(e)}")
                return Response(
                    {'error': 'Failed to update payment status. Please try again.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            return Response(
                {
                    'error': f'Submitted amount ({submitted_amount}) does not equal total amount ({sell.total_amount})',
                    'submitted_amount': submitted_amount,
                    'total_amount': sell.total_amount,
                    'difference': abs(sell.total_amount - submitted_amount)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Sell.DoesNotExist:
        return Response(
            {'error': 'Sell not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        print(f"Unexpected error updating payment status for sell {sell_id}: {str(e)}")
        return Response(
            {'error': 'An unexpected error occurred'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_delivery_schedule(request):
    """Get delivery schedule for sells with delivery dates."""
    try:
        # Filter based on user role
        if request.user.role == 'farmer':
            sells = Sell.objects.filter(
                farmer=request.user,
                sell_status__in=['purchased', 'completed'],
                delivery_date__isnull=False
            ).select_related('buyer', 'harvest_stock__harvest')
        elif request.user.role == 'buyer':
            sells = Sell.objects.filter(
                buyer=request.user,
                sell_status__in=['purchased', 'completed'],
                delivery_date__isnull=False
            ).select_related('farmer', 'harvest_stock__harvest')
        elif request.user.role in ['admin', 'minagri_officer']:
            sells = Sell.objects.filter(
                sell_status__in=['purchased', 'completed'],
                delivery_date__isnull=False
            ).select_related('farmer', 'buyer', 'harvest_stock__harvest')
        else:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Order by delivery date
        sells = sells.order_by('delivery_date')
        
        serializer = SellListSerializer(sells, many=True)
        
        return Response(
            {
                'count': sells.count(),
                'delivery_schedule': serializer.data
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        print(f"Error retrieving delivery schedule: {str(e)}")
        return Response(
            {'error': 'Failed to retrieve delivery schedule'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_overdue_deliveries(request):
    """Get overdue deliveries."""
    try:
        from django.utils import timezone
        today = timezone.now().date()
        
        # Filter based on user role
        if request.user.role == 'farmer':
            sells = Sell.objects.filter(
                farmer=request.user,
                sell_status__in=['purchased', 'completed'],
                delivery_date__lt=today
            ).select_related('buyer', 'harvest_stock__harvest')
        elif request.user.role == 'buyer':
            sells = Sell.objects.filter(
                buyer=request.user,
                sell_status__in=['purchased', 'completed'],
                delivery_date__lt=today
            ).select_related('farmer', 'harvest_stock__harvest')
        elif request.user.role in ['admin', 'minagri_officer']:
            sells = Sell.objects.filter(
                sell_status__in=['purchased', 'completed'],
                delivery_date__lt=today
            ).select_related('farmer', 'buyer', 'harvest_stock__harvest')
        else:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Order by delivery date (most overdue first)
        sells = sells.order_by('delivery_date')
        
        serializer = SellListSerializer(sells, many=True)
        
        return Response(
            {
                'count': sells.count(),
                'overdue_deliveries': serializer.data
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        print(f"Error retrieving overdue deliveries: {str(e)}")
        return Response(
            {'error': 'Failed to retrieve overdue deliveries'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_farmer_sells(request, farmer_id):
    """Get sells for a specific farmer (admin/minagri officers only)."""
    try:
        # Only admin and minagri officers can access this endpoint
        if request.user.role not in ['admin', 'minagri_officer']:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if farmer exists
        try:
            farmer = CustomUser.objects.get(id=farmer_id, role='farmer')
        except CustomUser.DoesNotExist:
            return Response(
                {'error': 'Farmer not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        sells = Sell.objects.filter(farmer=farmer).select_related(
            'buyer', 'harvest_stock__harvest'
        )
        serializer = SellListSerializer(sells, many=True)
        
        return Response(
            {
                'farmer_info': {
                    'id': farmer.id,
                    'phone_number': farmer.phone_number,
                    'email': farmer.email
                },
                'count': sells.count(),
                'sells': serializer.data
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        print(f"Error retrieving sells for farmer {farmer_id}: {str(e)}")
        return Response(
            {'error': 'Failed to retrieve farmer sells'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_buyer_purchases(request, buyer_id):
    """Get purchases for a specific buyer (admin/minagri officers only)."""
    try:
        # Only admin and minagri officers can access this endpoint
        if request.user.role not in ['admin', 'minagri_officer']:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if buyer exists
        try:
            buyer = CustomUser.objects.get(id=buyer_id, role='buyer')
        except CustomUser.DoesNotExist:
            return Response(
                {'error': 'Buyer not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        purchases = Sell.objects.filter(buyer=buyer).select_related(
            'farmer', 'harvest_stock__harvest'
        )
        serializer = SellListSerializer(purchases, many=True)
        
        return Response(
            {
                'buyer_info': {
                    'id': buyer.id,
                    'phone_number': buyer.phone_number,
                    'email': buyer.email
                },
                'count': purchases.count(),
                'purchases': serializer.data
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        print(f"Error retrieving purchases for buyer {buyer_id}: {str(e)}")
        return Response(
            {'error': 'Failed to retrieve buyer purchases'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
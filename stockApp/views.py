from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal, InvalidOperation
from .models import SunflowerHarvest, HarvestStock, HarvestMovement
from .serializers import (
    SunflowerHarvestSerializer, 
    HarvestStockSerializer, 
    HarvestMovementSerializer
)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_harvest_stock(request):
    """Create a new harvest and its corresponding stock entry."""
    try:
        data = request.data.copy()
        data['farmer'] = request.user.id
        
        # Validate required fields
        required_fields = ['harvest_date', 'quantity', 'quality_grade', 
                          'moisture_content', 'oil_content', 'district', 
                          'sector', 'cell', 'village']
        
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            print(f"Missing required fields: {missing_fields}")
            return Response({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate quantity is positive
        try:
            quantity = Decimal(str(data['quantity']))
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
        except (InvalidOperation, ValueError) as e:
            print(f"Invalid quantity: {data.get('quantity')} - {str(e)}")
            return Response({
                'error': 'Quantity must be a positive number'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # Create harvest
            harvest_serializer = SunflowerHarvestSerializer(data=data)
            if harvest_serializer.is_valid():
                harvest = harvest_serializer.save(farmer=request.user)
                
                # Create corresponding stock
                stock = HarvestStock.objects.create(
                    harvest=harvest,
                    current_quantity=harvest.quantity
                )
                
                print(f"Successfully created harvest {harvest.id} with stock {stock.id}")
                return Response({
                    'message': 'Harvest and stock created successfully',
                    'harvest': harvest_serializer.data,
                    'stock': HarvestStockSerializer(stock).data
                }, status=status.HTTP_201_CREATED)
            else:
                print(f"Harvest serializer errors: {harvest_serializer.errors}")
                return Response({
                    'error': 'Invalid harvest data',
                    'details': harvest_serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
    except Exception as e:
        print(f"Error creating harvest stock: {str(e)}")
        return Response({
            'error': 'An error occurred while creating harvest stock',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_stocks(request):
    """Get all harvest stocks with pagination and filtering."""
    try:
        stocks = HarvestStock.objects.select_related('harvest', 'harvest__farmer').all()
        
        # Filter by district if provided
        district = request.GET.get('district')
        if district:
            stocks = stocks.filter(harvest__district__icontains=district)
        
        # Filter by quality grade if provided
        quality_grade = request.GET.get('quality_grade')
        if quality_grade:
            stocks = stocks.filter(harvest__quality_grade=quality_grade)
        
        # Filter by minimum quantity if provided
        min_quantity = request.GET.get('min_quantity')
        if min_quantity:
            try:
                min_qty = Decimal(str(min_quantity))
                stocks = stocks.filter(current_quantity__gte=min_qty)
            except (InvalidOperation, ValueError):
                print(f"Invalid min_quantity parameter: {min_quantity}")
                pass
        
        serializer = HarvestStockSerializer(stocks, many=True)
        
        print(f"Retrieved {len(serializer.data)} stock records")
        return Response({
            'count': len(serializer.data),
            'stocks': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error retrieving all stocks: {str(e)}")
        return Response({
            'error': 'An error occurred while retrieving stocks',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_stock_details(request, stock_id):
    """Get detailed information about a specific stock."""
    try:
        stock = get_object_or_404(
            HarvestStock.objects.select_related('harvest', 'harvest__farmer'),
            id=stock_id
        )
        
        # Get recent movements
        recent_movements = HarvestMovement.objects.filter(
            stock=stock
        ).select_related('created_by')[:10]
        
        stock_data = HarvestStockSerializer(stock).data
        harvest_data = SunflowerHarvestSerializer(stock.harvest).data
        movements_data = HarvestMovementSerializer(recent_movements, many=True).data
        
        print(f"Retrieved details for stock {stock_id}")
        return Response({
            'stock': stock_data,
            'harvest': harvest_data,
            'recent_movements': movements_data,
            'availability_status': get_availability_status(stock.current_quantity, stock.harvest.quantity)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error retrieving stock details for ID {stock_id}: {str(e)}")
        return Response({
            'error': 'An error occurred while retrieving stock details',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_farmer_stocks(request):
    """Get all stocks created by the logged-in farmer."""
    try:
        stocks = HarvestStock.objects.filter(
            harvest__farmer=request.user
        ).select_related('harvest')
        
        serializer = HarvestStockSerializer(stocks, many=True)
        
        # Calculate summary statistics
        total_stocks = len(serializer.data)
        total_quantity = sum(Decimal(str(stock['current_quantity'])) for stock in serializer.data)
        
        print(f"Retrieved {total_stocks} stocks for farmer {request.user.id}")
        return Response({
            'count': total_stocks,
            'total_quantity': str(total_quantity),
            'stocks': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error retrieving farmer stocks for user {request.user.id}: {str(e)}")
        return Response({
            'error': 'An error occurred while retrieving your stocks',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_stock_movement(request):
    """Create stock in/out movements."""
    try:
        data = request.data.copy()
        
        # Validate required fields
        required_fields = ['stock_id', 'movement_type', 'quantity']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            print(f"Missing required fields for movement: {missing_fields}")
            return Response({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get stock
        try:
            stock = HarvestStock.objects.get(id=data['stock_id'])
        except HarvestStock.DoesNotExist:
            print(f"Stock not found: {data['stock_id']}")
            return Response({
                'error': 'Stock not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Validate quantity
        try:
            quantity = Decimal(str(data['quantity']))
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
        except (InvalidOperation, ValueError) as e:
            print(f"Invalid movement quantity: {data.get('quantity')} - {str(e)}")
            return Response({
                'error': 'Quantity must be a positive number'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate movement type
        valid_types = ['in', 'out', 'transfer', 'adjustment']
        if data['movement_type'] not in valid_types:
            print(f"Invalid movement type: {data['movement_type']}")
            return Response({
                'error': f'Invalid movement type. Must be one of: {", ".join(valid_types)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if transfer requires destination
        if data['movement_type'] == 'transfer':
            transfer_fields = ['to_district', 'to_sector', 'to_cell', 'to_village']
            missing_transfer_fields = [field for field in transfer_fields if not data.get(field)]
            if missing_transfer_fields:
                print(f"Missing transfer destination fields: {missing_transfer_fields}")
                return Response({
                    'error': f'Transfer requires destination: {", ".join(missing_transfer_fields)}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # Create movement
            movement = HarvestMovement(
                stock=stock,
                movement_type=data['movement_type'],
                quantity=quantity,
                notes=data.get('notes', ''),
                created_by=request.user
            )
            
            # Set transfer destination if applicable
            if data['movement_type'] == 'transfer':
                movement.to_district = data['to_district']
                movement.to_sector = data['to_sector']
                movement.to_cell = data['to_cell']
                movement.to_village = data['to_village']
            
            # Validate and save
            movement.full_clean()
            movement.save()
            
            serializer = HarvestMovementSerializer(movement)
            
            print(f"Successfully created {data['movement_type']} movement of {quantity} kg for stock {stock.id}")
            return Response({
                'message': 'Stock movement created successfully',
                'movement': serializer.data,
                'updated_stock_quantity': str(stock.current_quantity)
            }, status=status.HTTP_201_CREATED)
            
    except ValidationError as e:
        print(f"Validation error in stock movement: {str(e)}")
        return Response({
            'error': 'Validation failed',
            'details': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        print(f"Error creating stock movement: {str(e)}")
        return Response({
            'error': 'An error occurred while creating stock movement',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_stock(request, stock_id):
    """Update stock information (admin adjustment)."""
    try:
        stock = get_object_or_404(HarvestStock, id=stock_id)
        
        # Only allow quantity updates via adjustment movements
        if 'current_quantity' in request.data:
            try:
                new_quantity = Decimal(str(request.data['current_quantity']))
                if new_quantity < 0:
                    raise ValueError("Quantity cannot be negative")
                
                old_quantity = stock.current_quantity
                difference = new_quantity - old_quantity
                
                with transaction.atomic():
                    # Create adjustment movement
                    movement = HarvestMovement.objects.create(
                        stock=stock,
                        movement_type='adjustment',
                        quantity=abs(difference),
                        notes=f"Admin adjustment: {old_quantity} → {new_quantity}. {request.data.get('notes', '')}",
                        created_by=request.user
                    )
                    
                    # Update stock directly for adjustments
                    stock.current_quantity = new_quantity
                    stock.save()
                
                print(f"Stock {stock_id} adjusted from {old_quantity} to {new_quantity}")
                return Response({
                    'message': 'Stock updated successfully',
                    'stock': HarvestStockSerializer(stock).data,
                    'adjustment_movement': HarvestMovementSerializer(movement).data
                }, status=status.HTTP_200_OK)
                
            except (InvalidOperation, ValueError) as e:
                print(f"Invalid quantity for stock update: {request.data.get('current_quantity')} - {str(e)}")
                return Response({
                    'error': 'Invalid quantity value'
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                'error': 'No valid fields to update'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        print(f"Error updating stock {stock_id}: {str(e)}")
        return Response({
            'error': 'An error occurred while updating stock',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_stock(request, stock_id):
    """Delete a stock and its associated harvest (with validation)."""
    try:
        stock = get_object_or_404(
            HarvestStock.objects.select_related('harvest'), 
            id=stock_id
        )
        
        # Check if user owns this harvest or is admin
        if stock.harvest.farmer != request.user and not request.user.is_staff:
            print(f"Unauthorized deletion attempt by user {request.user.id} for stock {stock_id}")
            return Response({
                'error': 'You can only delete your own harvests'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if there are any movements
        movements_count = HarvestMovement.objects.filter(stock=stock).count()
        if movements_count > 0:
            print(f"Attempted to delete stock {stock_id} with {movements_count} movements")
            return Response({
                'error': f'Cannot delete stock with existing movements ({movements_count} movements found). Consider setting quantity to 0 instead.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        harvest_id = stock.harvest.id
        with transaction.atomic():
            stock.delete()  # This will also delete the harvest due to OneToOne relationship
        
        print(f"Successfully deleted stock {stock_id} and harvest {harvest_id}")
        return Response({
            'message': 'Stock and harvest deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)
        
    except Exception as e:
        print(f"Error deleting stock {stock_id}: {str(e)}")
        return Response({
            'error': 'An error occurred while deleting stock',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_harvest_availability_status(request):
    """Get harvest availability status with various filters."""
    try:
        stocks = HarvestStock.objects.select_related('harvest', 'harvest__farmer').all()
        
        # Apply filters
        district = request.GET.get('district')
        if district:
            stocks = stocks.filter(harvest__district__icontains=district)
        
        quality_grade = request.GET.get('quality_grade')
        if quality_grade:
            stocks = stocks.filter(harvest__quality_grade=quality_grade)
        
        status_filter = request.GET.get('status')  # 'available', 'low', 'empty'
        
        results = []
        available_count = low_stock_count = empty_count = 0
        total_available_quantity = Decimal('0')
        
        for stock in stocks:
            availability_status = get_availability_status(
                stock.current_quantity, 
                stock.harvest.quantity
            )
            
            # Count by status
            if availability_status['status'] == 'available':
                available_count += 1
                total_available_quantity += stock.current_quantity
            elif availability_status['status'] == 'low_stock':
                low_stock_count += 1
                total_available_quantity += stock.current_quantity
            else:
                empty_count += 1
            
            # Filter by status if requested
            if status_filter and availability_status['status'] != status_filter:
                continue
            
            stock_data = HarvestStockSerializer(stock).data
            stock_data['availability_status'] = availability_status
            results.append(stock_data)
        
        summary = {
            'total_stocks': len(stocks),
            'available_stocks': available_count,
            'low_stock_count': low_stock_count,
            'empty_stocks': empty_count,
            'total_available_quantity': str(total_available_quantity),
            'filtered_results': len(results)
        }
        
        print(f"Retrieved harvest availability status: {summary}")
        return Response({
            'summary': summary,
            'stocks': results
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error retrieving harvest availability status: {str(e)}")
        return Response({
            'error': 'An error occurred while retrieving availability status',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_stock_movements_history(request, stock_id):
    """Get complete movement history for a specific stock."""
    try:
        stock = get_object_or_404(HarvestStock, id=stock_id)
        
        movements = HarvestMovement.objects.filter(
            stock=stock
        ).select_related('created_by').order_by('-movement_date')
        
        serializer = HarvestMovementSerializer(movements, many=True)
        
        # Calculate movement summary
        total_in = sum(
            Decimal(str(m['quantity'])) for m in serializer.data 
            if m['movement_type'] == 'in'
        )
        total_out = sum(
            Decimal(str(m['quantity'])) for m in serializer.data 
            if m['movement_type'] in ['out', 'transfer']
        )
        
        print(f"Retrieved {len(serializer.data)} movements for stock {stock_id}")
        return Response({
            'stock_id': stock_id,
            'current_quantity': str(stock.current_quantity),
            'original_quantity': str(stock.harvest.quantity),
            'total_movements': len(serializer.data),
            'total_in': str(total_in),
            'total_out': str(total_out),
            'movements': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error retrieving movement history for stock {stock_id}: {str(e)}")
        return Response({
            'error': 'An error occurred while retrieving movement history',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard_summary(request):
    """Get dashboard summary for farmers and admins."""
    try:
        # Filter stocks based on user role
        if request.user.is_staff:
            stocks = HarvestStock.objects.select_related('harvest', 'harvest__farmer').all()
        else:
            stocks = HarvestStock.objects.filter(
                harvest__farmer=request.user
            ).select_related('harvest')
        
        total_stocks = stocks.count()
        total_harvests = sum(stock.harvest.quantity for stock in stocks)
        total_current = sum(stock.current_quantity for stock in stocks)
        
        # Status breakdown
        available = low_stock = empty = 0
        for stock in stocks:
            status = get_availability_status(stock.current_quantity, stock.harvest.quantity)
            if status['status'] == 'available':
                available += 1
            elif status['status'] == 'low_stock':
                low_stock += 1
            else:
                empty += 1
        
        # Recent activity
        recent_movements = HarvestMovement.objects.filter(
            stock__in=stocks
        ).select_related('stock', 'created_by').order_by('-movement_date')[:10]
        
        summary = {
            'total_stocks': total_stocks,
            'total_original_quantity': str(total_harvests),
            'total_current_quantity': str(total_current),
            'utilization_rate': str(round((total_current / total_harvests * 100) if total_harvests > 0 else 0, 2)),
            'status_breakdown': {
                'available': available,
                'low_stock': low_stock,
                'empty': empty
            },
            'recent_activity': HarvestMovementSerializer(recent_movements, many=True).data
        }
        
        print(f"Generated dashboard summary for user {request.user.id}")
        return Response(summary, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error generating dashboard summary for user {request.user.id}: {str(e)}")
        return Response({
            'error': 'An error occurred while generating dashboard summary',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def get_availability_status(current_qty, original_qty):
    """Helper function to determine availability status."""
    try:
        current = Decimal(str(current_qty))
        original = Decimal(str(original_qty))
        
        percentage = (current / original * 100) if original > 0 else 0
        
        if current == 0:
            return {
                'status': 'empty',
                'level': 'danger',
                'percentage': 0,
                'message': 'Stock is empty'
            }
        elif percentage <= 20:
            return {
                'status': 'low_stock',
                'level': 'warning',
                'percentage': float(percentage),
                'message': 'Low stock level'
            }
        else:
            return {
                'status': 'available',
                'level': 'success',
                'percentage': float(percentage),
                'message': 'Stock available'
            }
    except Exception as e:
        print(f"Error calculating availability status: {str(e)}")
        return {
            'status': 'unknown',
            'level': 'info',
            'percentage': 0,
            'message': 'Unable to determine status'
        }
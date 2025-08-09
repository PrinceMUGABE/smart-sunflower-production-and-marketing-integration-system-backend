from django.db import models
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db import transaction
from decimal import Decimal
import logging

from .models import Warehouse, Category, Commodity, WarehouseCommodity, InventoryMovement
from .serializers import (
    WarehouseSerializer, WarehouseSummarySerializer, CategorySerializer, 
    CommoditySerializer, WarehouseCommoditySerializer, InventoryMovementSerializer,
    AddCommodityToWarehouseSerializer, UpdateInventorySerializer
)

logger = logging.getLogger(__name__)

# ============ WAREHOUSE VIEWS ============

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_warehouse(request):
    try:
        serializer = WarehouseSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            logger.info(f"Warehouse created successfully by user {request.user.id}: {serializer.data}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        logger.warning(f"Warehouse creation validation error: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error creating warehouse: {str(e)}")
        return Response(
            {"error": "Failed to create warehouse", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_warehouses(request):
    try:
        # Use summary serializer for listing to improve performance
        warehouses = Warehouse.objects.all().order_by('-created_at')
        serializer = WarehouseSummarySerializer(warehouses, many=True)
        logger.info(f"Retrieved {len(warehouses)} warehouses")
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error listing warehouses: {str(e)}")
        return Response(
            {"error": "Failed to fetch warehouses", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def warehouse_detail(request, id):
    try:
        warehouse = get_object_or_404(Warehouse, id=id)
        
        if request.method == 'GET':
            serializer = WarehouseSerializer(warehouse)
            logger.info(f"Retrieved warehouse ID {id}")
            return Response(serializer.data)
            
        elif request.method == 'PUT':
            serializer = WarehouseSerializer(warehouse, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                logger.info(f"Updated warehouse ID {id}")
                return Response(serializer.data)
            logger.warning(f"Update validation error for warehouse {id}: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == 'DELETE':
            warehouse.delete()
            logger.info(f"Deleted warehouse ID {id}")
            return Response(status=status.HTTP_204_NO_CONTENT)
            
    except Exception as e:
        logger.error(f"Error in warehouse detail for ID {id}: {str(e)}")
        return Response(
            {"error": "Operation failed", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_warehouses(request):
    try:
        warehouses = Warehouse.objects.filter(created_by=request.user).order_by('-created_at')
        serializer = WarehouseSummarySerializer(warehouses, many=True)
        logger.info(f"Retrieved {len(warehouses)} warehouses for user {request.user.id}")
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error fetching user's warehouses: {str(e)}")
        return Response(
            {"error": "Failed to fetch user warehouses", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============ CATEGORY VIEWS ============

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def categories(request):
    if request.method == 'GET':
        try:
            categories = Category.objects.all().order_by('name')
            serializer = CategorySerializer(categories, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error fetching categories: {str(e)}")
            return Response(
                {"error": "Failed to fetch categories", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    elif request.method == 'POST':
        try:
            serializer = CategorySerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                logger.info(f"Category created: {serializer.data}")
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating category: {str(e)}")
            return Response(
                {"error": "Failed to create category", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def category_detail(request, id):
    try:
        category = get_object_or_404(Category, id=id)
        
        if request.method == 'GET':
            serializer = CategorySerializer(category)
            return Response(serializer.data)
            
        elif request.method == 'PUT':
            serializer = CategorySerializer(category, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == 'DELETE':
            # Check if category has commodities
            if category.commodities.exists():
                return Response(
                    {"error": "Cannot delete category with existing commodities"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            category.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
            
    except Exception as e:
        logger.error(f"Error in category detail for ID {id}: {str(e)}")
        return Response(
            {"error": "Operation failed", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============ COMMODITY VIEWS ============

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def commodities(request):
    if request.method == 'GET':
        try:
            commodities = Commodity.objects.all().order_by('category__name', 'name')
            serializer = CommoditySerializer(commodities, many=True)
            
            print(f"Retrieved {len(commodities)} commodities \n\n")
            print(f"Commodities data: {serializer.data} \n\n")
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error fetching commodities: {str(e)}")
            return Response(
                {"error": "Failed to fetch commodities", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    elif request.method == 'POST':
        try:
            serializer = CommoditySerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                logger.info(f"Commodity created: {serializer.data}")
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating commodity: {str(e)}")
            return Response(
                {"error": "Failed to create commodity", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def commodity_detail(request, id):
    try:
        commodity = get_object_or_404(Commodity, id=id)
        
        if request.method == 'GET':
            serializer = CommoditySerializer(commodity)
            
            
            print(f"Commodities data: {serializer.data} \n\n")
            
            return Response(serializer.data)
            
        elif request.method == 'PUT':
            serializer = CommoditySerializer(commodity, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == 'DELETE':
            # Check if commodity is used in warehouses
            if commodity.warehouse_commodities.exists():
                return Response(
                    {"error": "Cannot delete commodity that is stored in warehouses"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            commodity.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
            
    except Exception as e:
        logger.error(f"Error in commodity detail for ID {id}: {str(e)}")
        return Response(
            {"error": "Operation failed", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============ WAREHOUSE-COMMODITY MANAGEMENT ============

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_commodity_to_warehouse(request, warehouse_id):
    try:
        warehouse = get_object_or_404(Warehouse, id=warehouse_id)
        serializer = AddCommodityToWarehouseSerializer(data=request.data)
        
        if serializer.is_valid():
            commodity_id = serializer.validated_data['commodity_id']
            commodity = get_object_or_404(Commodity, id=commodity_id)
            
            # Check if commodity already exists in warehouse
            if WarehouseCommodity.objects.filter(warehouse=warehouse, commodity=commodity).exists():
                return Response(
                    {"error": "Commodity already exists in this warehouse"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic():
                warehouse_commodity = WarehouseCommodity.objects.create(
                    warehouse=warehouse,
                    commodity=commodity,
                    max_capacity=serializer.validated_data['max_capacity'],
                    current_quantity=serializer.validated_data['current_quantity'],
                    created_by=request.user
                )
                
                # Create initial inventory movement if there's starting quantity
                if warehouse_commodity.current_quantity > 0:
                    InventoryMovement.objects.create(
                        warehouse_commodity=warehouse_commodity,
                        movement_type='in',
                        quantity=warehouse_commodity.current_quantity,
                        notes='Initial stock',
                        created_by=request.user
                    )
            
            response_serializer = WarehouseCommoditySerializer(warehouse_commodity)
            logger.info(f"Added commodity {commodity.name} to warehouse {warehouse.location}")
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Error adding commodity to warehouse {warehouse_id}: {str(e)}")
        return Response(
            {"error": "Failed to add commodity to warehouse", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def warehouse_commodities(request, warehouse_id):
    try:
        warehouse = get_object_or_404(Warehouse, id=warehouse_id)
        warehouse_commodities = warehouse.warehouse_commodities.all().order_by('commodity__category__name', 'commodity__name')
        serializer = WarehouseCommoditySerializer(warehouse_commodities, many=True)
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error fetching warehouse commodities for warehouse {warehouse_id}: {str(e)}")
        return Response(
            {"error": "Failed to fetch warehouse commodities", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )





@api_view(['PUT', 'DELETE'])
@permission_classes([AllowAny])
def warehouse_commodity_detail(request, warehouse_id, commodity_id):
    try:
        warehouse_commodity = get_object_or_404(
            WarehouseCommodity, 
            warehouse_id=warehouse_id, 
            commodity_id=commodity_id
        )
        
        if request.method == 'PUT':
            serializer = WarehouseCommoditySerializer(warehouse_commodity, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == 'DELETE':
            warehouse_commodity.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
            
    except Exception as e:
        logger.error(f"Error in warehouse commodity detail: {str(e)}")
        return Response(
            {"error": "Operation failed", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============ INVENTORY MANAGEMENT ============

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_inventory(request):
    try:
        serializer = UpdateInventorySerializer(data=request.data)
        if serializer.is_valid():
            warehouse_commodity_id = serializer.validated_data['warehouse_commodity_id']
            quantity = serializer.validated_data['quantity']
            movement_type = serializer.validated_data['movement_type']
            
            warehouse_commodity = get_object_or_404(WarehouseCommodity, id=warehouse_commodity_id)
            
            with transaction.atomic():
                success = False
                if movement_type == 'in':
                    success = warehouse_commodity.add_quantity(quantity)
                elif movement_type == 'out':
                    success = warehouse_commodity.remove_quantity(quantity)
                elif movement_type == 'adjustment':
                    # For adjustments, set the quantity directly
                    warehouse_commodity.current_quantity = quantity
                    warehouse_commodity.save()
                    success = True
                
                if success:
                    # Create inventory movement record
                    InventoryMovement.objects.create(
                        warehouse_commodity=warehouse_commodity,
                        movement_type=movement_type,
                        quantity=quantity,
                        reference_number=serializer.validated_data.get('reference_number', ''),
                        notes=serializer.validated_data.get('notes', ''),
                        created_by=request.user
                    )
                    
                    response_serializer = WarehouseCommoditySerializer(warehouse_commodity)
                    return Response(response_serializer.data)
                else:
                    error_msg = "Insufficient capacity" if movement_type == 'in' else "Insufficient quantity"
                    return Response(
                        {"error": error_msg},
                        status=status.HTTP_400_BAD_REQUEST
                    )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Error updating inventory: {str(e)}")
        return Response(
            {"error": "Failed to update inventory", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def warehouse_movements(request, warehouse_id):
    """
    Get all inventory movements for a specific warehouse
    """
    try:
        # Get the warehouse
        warehouse = get_object_or_404(Warehouse, id=warehouse_id)
        
        # Get all warehouse commodities for this warehouse
        warehouse_commodities = WarehouseCommodity.objects.filter(warehouse=warehouse)
        
        # Get all movements for these warehouse commodities
        movements = InventoryMovement.objects.filter(
            warehouse_commodity__in=warehouse_commodities
        ).order_by('-created_at')
        
        # Serialize the movements
        serializer = InventoryMovementSerializer(movements, many=True)
        
        return Response({
            'warehouse': {
                'id': warehouse.id,
                'location': warehouse.location,
                'status': warehouse.status,
                'availability_status': warehouse.availability_status
            },
            'movements': serializer.data,
            'total_movements': movements.count()
        })
        
    except Exception as e:
        logger.error(f"Error fetching warehouse movements: {str(e)}")
        return Response(
            {"error": "Failed to fetch warehouse movements", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============ REPORTING VIEWS ============

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def warehouse_capacity_report(request):
    try:
        warehouses = Warehouse.objects.all()
        report_data = []
        
        for warehouse in warehouses:
            warehouse_data = {
                'warehouse_id': warehouse.id,
                'location': warehouse.location,
                'status': warehouse.status,
                'availability_status': warehouse.availability_status,
                'total_commodities': warehouse.warehouse_commodities.count(),
                'total_capacity_utilization': round(warehouse.get_total_capacity_utilization(), 2),
                'commodities': []
            }
            
            for wc in warehouse.warehouse_commodities.all():
                commodity_data = {
                    'commodity_name': wc.commodity.name,
                    'category': wc.commodity.category.name,
                    'max_capacity': float(wc.max_capacity),
                    'current_quantity': float(wc.current_quantity),
                    'available_capacity': float(wc.get_available_capacity()),
                    'utilization_percentage': round(wc.get_capacity_utilization(), 2),
                    'unit': wc.commodity.unit_of_measurement,
                    'is_at_capacity': wc.is_at_capacity()
                }
                warehouse_data['commodities'].append(commodity_data)
            
            report_data.append(warehouse_data)
        
        return Response(report_data)
        
    except Exception as e:
        logger.error(f"Error generating capacity report: {str(e)}")
        return Response(
            {"error": "Failed to generate capacity report", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        
        
        
        
        
        



# Add these view functions to your existing views.py file

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def warehouse_categories(request, warehouse_id):
    """
    Get all categories that have commodities available in a specific warehouse
    """
    try:
        warehouse = get_object_or_404(Warehouse, id=warehouse_id)
        
        # Get all categories that have commodities stored in this warehouse
        categories = Category.objects.filter(
            commodities__warehouse_commodities__warehouse=warehouse
        ).distinct().order_by('name')
        
        serializer = CategorySerializer(categories, many=True)
        
        print(f"Retrieved {len(categories)} categories for warehouse {warehouse_id}")
        
        return Response({
            'warehouse': {
                'id': warehouse.id,
                'location': warehouse.location,
                'status': warehouse.status,
                'availability_status': warehouse.availability_status
            },
            'categories': serializer.data,
            'total_categories': categories.count()
        })
        
    except Exception as e:
        print(f"Error fetching categories for warehouse {warehouse_id}: {str(e)}")
        return Response(
            {"error": "Failed to fetch warehouse categories", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def warehouse_available_categories(request, warehouse_id):
    """
    Get all categories that have commodities with available capacity in a specific warehouse
    """
    try:
        warehouse = get_object_or_404(Warehouse, id=warehouse_id)
        
        # Get categories that have commodities with available capacity (not at full capacity)
        categories = Category.objects.filter(
            commodities__warehouse_commodities__warehouse=warehouse,
            commodities__warehouse_commodities__current_quantity__lt=models.F(
                'commodities__warehouse_commodities__max_capacity'
            )
        ).distinct().order_by('name')
        
        serializer = CategorySerializer(categories, many=True)
        
        logger.info(f"Retrieved {len(categories)} available categories for warehouse {warehouse_id}")
        
        return Response({
            'warehouse': {
                'id': warehouse.id,
                'location': warehouse.location,
                'status': warehouse.status,
                'availability_status': warehouse.availability_status
            },
            'categories': serializer.data,
            'total_categories': categories.count()
        })
        
    except Exception as e:
        logger.error(f"Error fetching available categories for warehouse {warehouse_id}: {str(e)}")
        return Response(
            {"error": "Failed to fetch warehouse available categories", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def category_commodities(request, category_id):
    """
    Get all commodities that belong to a specific category
    """
    try:
        category = get_object_or_404(Category, id=category_id)
        
        # Get all commodities in this category
        commodities = Commodity.objects.filter(category=category).order_by('name')
        
        serializer = CommoditySerializer(commodities, many=True)
        
        logger.info(f"Retrieved {len(commodities)} commodities for category {category_id}")
        
        return Response({
            'category': {
                'id': category.id,
                'name': category.name,
                'description': category.description
            },
            'commodities': serializer.data,
            'total_commodities': commodities.count()
        })
        
    except Exception as e:
        logger.error(f"Error fetching commodities for category {category_id}: {str(e)}")
        return Response(
            {"error": "Failed to fetch category commodities", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def warehouse_category_commodities(request, warehouse_id, category_id):
    """
    Get all commodities of a specific category that are available in a specific warehouse
    """
    try:
        warehouse = get_object_or_404(Warehouse, id=warehouse_id)
        category = get_object_or_404(Category, id=category_id)
        
        # Get commodities in this category that are stored in this warehouse
        commodities = Commodity.objects.filter(
            category=category,
            warehouse_commodities__warehouse=warehouse
        ).distinct().order_by('name')
        
        # Create response data with warehouse commodity details
        commodities_data = []
        for commodity in commodities:
            warehouse_commodity = WarehouseCommodity.objects.get(
                warehouse=warehouse,
                commodity=commodity
            )
            
            commodity_data = {
                'id': commodity.id,
                'name': commodity.name,
                'unit_of_measurement': commodity.unit_of_measurement,
                'description': commodity.description,
                'warehouse_commodity': {
                    'max_capacity': float(warehouse_commodity.max_capacity),
                    'current_quantity': float(warehouse_commodity.current_quantity),
                    'available_capacity': float(warehouse_commodity.get_available_capacity()),
                    'capacity_utilization': round(warehouse_commodity.get_capacity_utilization(), 2),
                    'is_at_capacity': warehouse_commodity.is_at_capacity()
                }
            }
            commodities_data.append(commodity_data)
        
        logger.info(f"Retrieved {len(commodities)} commodities for warehouse {warehouse_id} and category {category_id}")
        
        return Response({
            'warehouse': {
                'id': warehouse.id,
                'location': warehouse.location,
                'status': warehouse.status,
                'availability_status': warehouse.availability_status
            },
            'category': {
                'id': category.id,
                'name': category.name,
                'description': category.description
            },
            'commodities': commodities_data,
            'total_commodities': len(commodities_data)
        })
        
    except Exception as e:
        logger.error(f"Error fetching commodities for warehouse {warehouse_id} and category {category_id}: {str(e)}")
        return Response(
            {"error": "Failed to fetch warehouse category commodities", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def warehouse_category_available_commodities(request, warehouse_id, category_id):
    """
    Get all commodities of a specific category that have available capacity in a specific warehouse
    """
    try:
        warehouse = get_object_or_404(Warehouse, id=warehouse_id)
        category = get_object_or_404(Category, id=category_id)
        
        # Get commodities in this category that have available capacity in this warehouse
        warehouse_commodities = WarehouseCommodity.objects.filter(
            warehouse=warehouse,
            commodity__category=category,
            current_quantity__lt=models.F('max_capacity')
        ).select_related('commodity').order_by('commodity__name')
        
        # Create response data
        commodities_data = []
        for wc in warehouse_commodities:
            commodity_data = {
                'id': wc.commodity.id,
                'name': wc.commodity.name,
                'unit_of_measurement': wc.commodity.unit_of_measurement,
                'description': wc.commodity.description,
                'warehouse_commodity': {
                    'max_capacity': float(wc.max_capacity),
                    'current_quantity': float(wc.current_quantity),
                    'available_capacity': float(wc.get_available_capacity()),
                    'capacity_utilization': round(wc.get_capacity_utilization(), 2),
                    'is_at_capacity': wc.is_at_capacity()
                }
            }
            commodities_data.append(commodity_data)
        
        logger.info(f"Retrieved {len(commodities_data)} available commodities for warehouse {warehouse_id} and category {category_id}")
        
        return Response({
            'warehouse': {
                'id': warehouse.id,
                'location': warehouse.location,
                'status': warehouse.status,
                'availability_status': warehouse.availability_status
            },
            'category': {
                'id': category.id,
                'name': category.name,
                'description': category.description
            },
            'commodities': commodities_data,
            'total_commodities': len(commodities_data)
        })
        
    except Exception as e:
        logger.error(f"Error fetching available commodities for warehouse {warehouse_id} and category {category_id}: {str(e)}")
        return Response(
            {"error": "Failed to fetch warehouse category available commodities", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def all_categories_with_commodities(request):
    """
    Get all categories with their commodities (useful for dropdowns)
    """
    try:
        categories = Category.objects.prefetch_related('commodities').order_by('name')
        
        categories_data = []
        for category in categories:
            commodities = category.commodities.all().order_by('name')
            commodities_data = []
            
            for commodity in commodities:
                commodities_data.append({
                    'id': commodity.id,
                    'name': commodity.name,
                    'unit_of_measurement': commodity.unit_of_measurement,
                    'description': commodity.description
                })
            
            category_data = {
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'commodities_count': len(commodities_data),
                'commodities': commodities_data
            }
            categories_data.append(category_data)
        
        logger.info(f"Retrieved {len(categories)} categories with their commodities")
        
        return Response({
            'categories': categories_data,
            'total_categories': len(categories_data)
        })
        
    except Exception as e:
        logger.error(f"Error fetching categories with commodities: {str(e)}")
        return Response(
            {"error": "Failed to fetch categories with commodities", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        
        
        
        
        
        
        
        
        
        
        
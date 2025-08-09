# serializers.py - Updated with payment fields

from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import Order
from warehouseApp.models import Warehouse, Category, Commodity, WarehouseCommodity, InventoryMovement
from userApp.models import CustomUser
from decimal import Decimal

from stockApp.models import StorageCost


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'phone_number', 'email', 'role', 'created_at']
        read_only_fields = ['created_at']


class CategorySerializer(serializers.ModelSerializer):
    created_by = CustomUserSerializer(read_only=True)
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'created_by', 'created_at']


class CommoditySerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    
    class Meta:
        model = Commodity
        fields = ['id', 'name', 'category', 'unit_of_measurement', 'description', 'created_at']


class WarehouseSerializer(serializers.ModelSerializer):
    total_capacity_utilization = serializers.SerializerMethodField()
    
    class Meta:
        model = Warehouse
        fields = ['id', 'location', 'availability_status', 'status', 'created_at', 'total_capacity_utilization']
    
    def get_total_capacity_utilization(self, obj):
        return round(obj.get_total_capacity_utilization(), 2)


class InventoryMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryMovement
        fields = ['id', 'movement_type', 'quantity', 'reference_number', 'notes', 'created_at']


class OrderSerializer(serializers.ModelSerializer):
    # Read-only fields for detailed information
    warehouse_detail = WarehouseSerializer(source='warehouse', read_only=True)
    commodity_detail = CommoditySerializer(source='commodity', read_only=True)
    category_detail = CategorySerializer(source='category', read_only=True)
    inventory_movement_detail = InventoryMovementSerializer(source='inventory_movement', read_only=True)
    
    # User information
    user = CustomUserSerializer(read_only=True)
    
    # Capacity information
    available_warehouse_capacity = serializers.SerializerMethodField()
    can_be_stored = serializers.SerializerMethodField()
    
    # Status display
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    availability_status_display = serializers.CharField(source='get_availability_status_display', read_only=True)
    
    # Payment status display
    payment_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'origin', 'cost_charged', 'status', 'status_display', 'availability_status', 
            'availability_status_display', 'warehouse', 'commodity', 'category', 'quantity', 
            'phone_number', 'is_paid', 'payment_status', 'created_at', 'updated_at', 'user',
            # Detailed information
            'warehouse_detail', 'commodity_detail', 'category_detail', 'inventory_movement_detail',
            # Capacity information
            'available_warehouse_capacity', 'can_be_stored'
        ]
        read_only_fields = ['inventory_movement', 'created_at', 'updated_at']
    
    def get_available_warehouse_capacity(self, obj):
        return float(obj.get_available_warehouse_capacity())
    
    def get_can_be_stored(self, obj):
        return obj.can_be_stored()
    
    def get_payment_status(self, obj):
        return "Paid" if obj.is_paid else "Unpaid"
    
    def validate_phone_number(self, value):
        """Validate phone number format"""
        import re
        if not re.match(r'^\+?[0-9]{9,15}$', value):
            raise serializers.ValidationError(
                "Invalid phone number format. Please use a valid international format."
            )
        return value
    
    def validate(self, data):
        """Validate order data"""
        # Check if commodity belongs to category
        if data.get('commodity') and data.get('category'):
            if data['commodity'].category != data['category']:
                raise serializers.ValidationError({
                    'commodity': 'Selected commodity does not belong to the specified category'
                })
        
        # Check warehouse capacity
        if data.get('warehouse') and data.get('commodity') and data.get('quantity'):
            try:
                warehouse_commodity = WarehouseCommodity.objects.get(
                    warehouse=data['warehouse'],
                    commodity=data['commodity']
                )
                if not warehouse_commodity.can_add_quantity(data['quantity']):
                    available_capacity = warehouse_commodity.get_available_capacity()
                    raise serializers.ValidationError({
                        'quantity': f"Insufficient warehouse capacity. Available: {available_capacity} {data['commodity'].unit_of_measurement}"
                    })
            except WarehouseCommodity.DoesNotExist:
                raise serializers.ValidationError({
                    'warehouse': 'This warehouse does not support the selected commodity'
                })
        
        return data
    
    def create(self, validated_data):
        """Create order with current user"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class OrderUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating orders (limited fields)"""
    
    class Meta:
        model = Order
        fields = ['origin', 'cost_charged', 'warehouse', 'commodity', 'category', 'quantity', 'phone_number', 'is_paid']
    
    def validate_phone_number(self, value):
        """Validate phone number format"""
        import re
        if not re.match(r'^\+?[0-9]{9,15}$', value):
            raise serializers.ValidationError(
                "Invalid phone number format. Please use a valid international format."
            )
        return value
    
    def validate(self, data):
        """Validate update data"""
        instance = self.instance
        
        # Only allow updates for pending orders (except payment status)
        if instance and instance.status != 'pending':
            # Allow only payment status updates for non-pending orders
            allowed_fields = {'is_paid'}
            data_fields = set(data.keys())
            if not data_fields.issubset(allowed_fields):
                raise serializers.ValidationError(
                    "Only payment status can be updated for non-pending orders"
                )
        
        # Check if commodity belongs to category
        commodity = data.get('commodity', instance.commodity if instance else None)
        category = data.get('category', instance.category if instance else None)
        
        if commodity and category and commodity.category != category:
            raise serializers.ValidationError({
                'commodity': 'Selected commodity does not belong to the specified category'
            })
        
        # Check warehouse capacity for new quantity
        warehouse = data.get('warehouse', instance.warehouse if instance else None)
        quantity = data.get('quantity', instance.quantity if instance else None)
        
        if warehouse and commodity and quantity:
            try:
                warehouse_commodity = WarehouseCommodity.objects.get(
                    warehouse=warehouse,
                    commodity=commodity
                )
                
                # Calculate available capacity considering current order quantity
                current_order_quantity = instance.quantity if instance else 0
                available_capacity = warehouse_commodity.get_available_capacity() + current_order_quantity
                
                if quantity > available_capacity:
                    raise serializers.ValidationError({
                        'quantity': f"Insufficient warehouse capacity. Available: {available_capacity} {commodity.unit_of_measurement}"
                    })
            except WarehouseCommodity.DoesNotExist:
                raise serializers.ValidationError({
                    'warehouse': 'This warehouse does not support the selected commodity'
                })
        
        return data


class OrderActionSerializer(serializers.Serializer):
    """Serializer for order actions (confirm/reject)"""
    reason = serializers.CharField(required=False, max_length=500, help_text="Reason for action")


class OrderPaymentSerializer(serializers.Serializer):
    """Serializer for payment operations"""
    phone_number = serializers.CharField(max_length=20, required=False, help_text="Update payment phone number")
    is_paid = serializers.BooleanField(required=True, help_text="Payment status")
    
    def validate_phone_number(self, value):
        """Validate phone number format"""
        import re
        if value and not re.match(r'^\+?[0-9]{9,15}$', value):
            raise serializers.ValidationError(
                "Invalid phone number format. Please use a valid international format."
            )
        return value


class WarehouseCapacitySerializer(serializers.Serializer):
    """Serializer for checking warehouse capacity"""
    warehouse_id = serializers.IntegerField()
    commodity_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    def validate(self, data):
        """Validate capacity check data"""
        try:
            warehouse = Warehouse.objects.get(id=data['warehouse_id'])
            commodity = Commodity.objects.get(id=data['commodity_id'])
            
            try:
                warehouse_commodity = WarehouseCommodity.objects.get(
                    warehouse=warehouse,
                    commodity=commodity
                )
                data['warehouse_commodity'] = warehouse_commodity
                data['warehouse'] = warehouse
                data['commodity'] = commodity
            except WarehouseCommodity.DoesNotExist:
                raise serializers.ValidationError(
                    "This warehouse does not support the selected commodity"
                )
                
        except (Warehouse.DoesNotExist, Commodity.DoesNotExist):
            raise serializers.ValidationError(
                "Invalid warehouse or commodity ID"
            )
        
        return data
    
    

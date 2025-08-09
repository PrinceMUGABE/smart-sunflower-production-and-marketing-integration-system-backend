from rest_framework import serializers
from .models import Warehouse, Category, Commodity, WarehouseCommodity, InventoryMovement
from userApp.models import CustomUser
from decimal import Decimal


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'phone_number', 'email', 'role']


class CategorySerializer(serializers.ModelSerializer):
    commodities_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'created_at', 'commodities_count']
        read_only_fields = ('created_at',)
    
    def get_commodities_count(self, obj):
        return obj.commodities.count()
    
    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Category name cannot be empty")
        return value.strip()


class CommoditySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    warehouses_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Commodity
        fields = ['id', 'name', 'category', 'category_name', 'unit_of_measurement', 
                 'description', 'created_at', 'warehouses_count']
        read_only_fields = ('created_at',)
    
    def get_warehouses_count(self, obj):
        return obj.warehouse_commodities.count()
    
    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Commodity name cannot be empty")
        return value.strip()


class WarehouseCommoditySerializer(serializers.ModelSerializer):
    commodity_name = serializers.CharField(source='commodity.name', read_only=True)
    commodity_unit = serializers.CharField(source='commodity.unit_of_measurement', read_only=True)
    category_name = serializers.CharField(source='commodity.category.name', read_only=True)
    available_capacity = serializers.SerializerMethodField()
    capacity_utilization = serializers.SerializerMethodField()
    is_at_capacity = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.phone_number', read_only=True)
    
    class Meta:
        model = WarehouseCommodity
        fields = ['id', 'warehouse', 'commodity', 'commodity_name', 'commodity_unit', 
                 'category_name', 'max_capacity', 'current_quantity', 'available_capacity',
                 'capacity_utilization', 'is_at_capacity', 'created_at', 'updated_at',
                 'created_by', 'created_by_name']
        read_only_fields = ('created_at', 'updated_at', 'created_by')
    
    def get_available_capacity(self, obj):
        return float(obj.get_available_capacity())
    
    def get_capacity_utilization(self, obj):
        return round(obj.get_capacity_utilization(), 2)
    
    def get_is_at_capacity(self, obj):
        return obj.is_at_capacity()
    
    def validate(self, data):
        # Validate max_capacity is positive
        if 'max_capacity' in data and data['max_capacity'] <= 0:
            raise serializers.ValidationError({"max_capacity": "Maximum capacity must be greater than 0"})
        
        # Validate current_quantity doesn't exceed max_capacity
        max_capacity = data.get('max_capacity', getattr(self.instance, 'max_capacity', None))
        current_quantity = data.get('current_quantity', getattr(self.instance, 'current_quantity', 0))
        
        if max_capacity and current_quantity > max_capacity:
            raise serializers.ValidationError({
                "current_quantity": "Current quantity cannot exceed maximum capacity"
            })
        
        # Validate current_quantity is not negative
        if 'current_quantity' in data and data['current_quantity'] < 0:
            raise serializers.ValidationError({"current_quantity": "Current quantity cannot be negative"})
        
        return data


class WarehouseSerializer(serializers.ModelSerializer):
    created_by = CustomUserSerializer(read_only=True)
    warehouse_commodities = WarehouseCommoditySerializer(many=True, read_only=True)
    total_commodities = serializers.SerializerMethodField()
    total_capacity_utilization = serializers.SerializerMethodField()
    available_commodities_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Warehouse
        fields = ['id', 'location', 'availability_status', 'status', 'created_at', 
                 'created_by', 'commodities', 'warehouse_commodities', 'total_commodities',
                 'total_capacity_utilization', 'available_commodities_count']
        read_only_fields = ('created_at', 'created_by', 'commodities')
    
    def get_total_commodities(self, obj):
        return obj.warehouse_commodities.count()
    
    def get_total_capacity_utilization(self, obj):
        return round(obj.get_total_capacity_utilization(), 2)
    
    def get_available_commodities_count(self, obj):
        return obj.get_available_commodities().count()

    def validate(self, data):
        # Validate location is not empty
        if 'location' in data and not data['location'].strip():
            raise serializers.ValidationError({"location": "Location cannot be empty"})
        
        # Validate status and availability_status values
        valid_statuses = [choice[0] for choice in Warehouse.STATUS_CHOICES]
        if 'status' in data and data['status'] not in valid_statuses:
            raise serializers.ValidationError({"status": f"Must be one of {valid_statuses}"})
            
        valid_availabilities = [choice[0] for choice in Warehouse.AVAILABILITY_CHOICES]
        if 'availability_status' in data and data['availability_status'] not in valid_availabilities:
            raise serializers.ValidationError({"availability_status": f"Must be one of {valid_availabilities}"})
        
        return data


class InventoryMovementSerializer(serializers.ModelSerializer):
    warehouse_location = serializers.CharField(source='warehouse_commodity.warehouse.location', read_only=True)
    commodity_name = serializers.CharField(source='warehouse_commodity.commodity.name', read_only=True)
    commodity_unit = serializers.CharField(source='warehouse_commodity.commodity.unit_of_measurement', read_only=True)
    created_by_name = serializers.CharField(source='created_by.phone_number', read_only=True)
    
    class Meta:
        model = InventoryMovement
        fields = ['id', 'warehouse_commodity', 'warehouse_location', 'commodity_name', 
                 'commodity_unit', 'movement_type', 'quantity', 'reference_number', 
                 'notes', 'created_at', 'created_by', 'created_by_name']
        read_only_fields = ('created_at', 'created_by')
    
    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value


# Specialized serializers for specific use cases
class WarehouseSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for warehouse listings"""
    created_by_name = serializers.CharField(source='created_by.phone_number', read_only=True)
    total_commodities = serializers.SerializerMethodField()
    
    class Meta:
        model = Warehouse
        fields = ['id', 'location', 'availability_status', 'status', 'created_at', 
                 'created_by_name', 'total_commodities']
        read_only_fields = ('created_at',)
    
    def get_total_commodities(self, obj):
        return obj.warehouse_commodities.count()


class AddCommodityToWarehouseSerializer(serializers.Serializer):
    """Serializer for adding commodities to warehouses"""
    commodity_id = serializers.IntegerField()
    max_capacity = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=0.01)
    current_quantity = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=0, default=0)
    
    def validate_commodity_id(self, value):
        try:
            Commodity.objects.get(id=value)
        except Commodity.DoesNotExist:
            raise serializers.ValidationError("Commodity does not exist")
        return value
    
    def validate(self, data):
        if data['current_quantity'] > data['max_capacity']:
            raise serializers.ValidationError("Current quantity cannot exceed maximum capacity")
        return data


class UpdateInventorySerializer(serializers.Serializer):
    """Serializer for updating inventory quantities"""
    warehouse_commodity_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=15, decimal_places=2)
    movement_type = serializers.ChoiceField(choices=InventoryMovement.MOVEMENT_TYPES)
    reference_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_warehouse_commodity_id(self, value):
        try:
            WarehouseCommodity.objects.get(id=value)
        except WarehouseCommodity.DoesNotExist:
            raise serializers.ValidationError("Warehouse commodity does not exist")
        return value
    
    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value
    
    
    
    
    
    
    
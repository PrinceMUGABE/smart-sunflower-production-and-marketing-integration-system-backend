# serializers.py - Create this file or add to existing serializers

from rest_framework import serializers
from .models import OrderDelivery, Order
from userApp.models import CustomUser
from driverApp.models import Driver
from vehicleApp.models import Vehicle
from orderApp.models import WarehouseCommodity, InventoryMovement, Category, Commodity, Warehouse


# serializers.py - Updated with payment fields

from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from orderApp.models import Order
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


class OrderDetailSerializer(serializers.ModelSerializer):
    """Serializer for order details in delivery"""
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    commodity_name = serializers.CharField(source='commodity.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'origin', 'cost_charged', 'quantity', 'phone_number',
            'is_paid', 'status', 'availability_status', 'created_at',
            'warehouse_name', 'commodity_name', 'category_name', 'user_name'
        ]
    
    def get_user_name(self, obj):
        return f"{obj.user.email}".strip() or obj.user.phone_number

class DriverDetailSerializer(serializers.ModelSerializer):
    """Serializer for driver details in delivery"""
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Driver
        fields = [
            'id', 'gender', 'national_id_number',
            'driving_license_number', 'driving_categories', 'availability_status',
            'status', 'user_name'
        ]
    
    def get_user_name(self, obj):
        return obj.user.phone_number if obj.user else "Unknown User"

class VehicleDetailSerializer(serializers.ModelSerializer):
    """Serializer for vehicle details in delivery"""
    image_base64 = serializers.SerializerMethodField()
    
    class Meta:
        model = Vehicle
        fields = [
            'id', 'type', 'relocation_size', 'driving_category', 'status',
            'vehicle_model', 'plate_number', 'image_base64'
        ]
    
    def get_image_base64(self, obj):
        return obj.get_image_base64()


class DriverSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer(read_only=True)
    class Meta:
        model = Driver
        fields = '__all__'
        
        
class OrderDeliverySerializer(serializers.ModelSerializer):
    """Main serializer for order deliveries"""
    order_details = OrderDetailSerializer(source='order', read_only=True)
    driver_details = DriverDetailSerializer(source='driver', read_only=True)
    vehicle_details = VehicleDetailSerializer(source='vehicle', read_only=True)
    warehouse = OrderSerializer(source='order', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    driver = DriverSerializer(read_only=True)
  
    
    class Meta:
        model = OrderDelivery
        fields = [
            'id', 'order', 'vehicle', 'driver', 'status', 'created_by',
            'created_at', 'updated_at', 'order_details', 'driver_details',
            'vehicle_details', 'created_by_name', 'warehouse', 'driver'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']
    
    def get_created_by_name(self, obj):
        return f"{obj.created_by.email}".strip() or obj.created_by.phone_number
    
    def validate_order(self, value):
        """Validate order"""
        if not value:
            raise serializers.ValidationError("Order is required")
        
        if value.status != 'confirmed':
            raise serializers.ValidationError("Only confirmed orders can be assigned for delivery")
        
        if value.availability_status != 'imported':
            raise serializers.ValidationError("Order must be imported before delivery can be assigned")
        
        # Check if order already has a delivery
        if OrderDelivery.objects.filter(order=value).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise serializers.ValidationError("This order already has a delivery assigned")
        
        return value
    
    def validate_driver(self, value):
        """Validate driver"""
        if not value:
            raise serializers.ValidationError("Driver is required")
        
        if value.status != 'approved':
            raise serializers.ValidationError("Only approved drivers can be assigned to deliveries")
        
        if value.availability_status != 'active':
            raise serializers.ValidationError("Driver must be active to be assigned to deliveries")
        
        return value
    
    def validate_vehicle(self, value):
        """Validate vehicle"""
        if not value:
            raise serializers.ValidationError("Vehicle is required")
        
        if value.status != 'active':
            raise serializers.ValidationError("Only active vehicles can be assigned to deliveries")
        
        return value
    
    def validate(self, attrs):
        """Cross-field validation"""
        driver = attrs.get('driver')
        vehicle = attrs.get('vehicle')
        status = attrs.get('status', 'in_process')
        
        if driver and vehicle:
            # Check if driver can handle the vehicle's driving category
            if not driver.can_handle_driving_category(vehicle.driving_category):
                raise serializers.ValidationError({
                    'driver': f"Driver cannot handle vehicles of category {vehicle.driving_category}"
                })
        
        if status == 'in_process':
            # Check if driver is already assigned to another in-process delivery
            if driver:
                existing_delivery = OrderDelivery.objects.filter(
                    driver=driver,
                    status='in_process'
                ).exclude(pk=self.instance.pk if self.instance else None)
                
                if existing_delivery.exists():
                    raise serializers.ValidationError({
                        'driver': "Driver is already assigned to another in-process delivery"
                    })
            
            # Check if vehicle is already assigned to another in-process delivery
            if vehicle:
                existing_delivery = OrderDelivery.objects.filter(
                    vehicle=vehicle,
                    status='in_process'
                ).exclude(pk=self.instance.pk if self.instance else None)
                
                if existing_delivery.exists():
                    raise serializers.ValidationError({
                        'vehicle': "Vehicle is already assigned to another in-process delivery"
                    })
        
        return attrs

class OrderDeliveryCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating deliveries"""
    
    class Meta:
        model = OrderDelivery
        fields = ['order', 'vehicle', 'driver', 'status']
    
    def validate_order(self, value):
        """Validate order"""
        if not value:
            raise serializers.ValidationError("Order is required")
        
        if value.status != 'confirmed':
            raise serializers.ValidationError("Only confirmed orders can be assigned for delivery")
        
        if value.availability_status != 'imported':
            raise serializers.ValidationError("Order must be imported before delivery can be assigned")
        
        # Check if order already has a delivery (only for create)
        if not self.instance and OrderDelivery.objects.filter(order=value).exists():
            raise serializers.ValidationError("This order already has a delivery assigned")
        
        return value
    
    def validate_driver(self, value):
        """Validate driver"""
        if not value:
            raise serializers.ValidationError("Driver is required")
        
        if value.status != 'approved':
            raise serializers.ValidationError("Only approved drivers can be assigned to deliveries")
        
        if value.availability_status != 'active':
            raise serializers.ValidationError("Driver must be active to be assigned to deliveries")
        
        return value
    
    def validate_vehicle(self, value):
        """Validate vehicle"""
        if not value:
            raise serializers.ValidationError("Vehicle is required")
        
        if value.status != 'active':
            raise serializers.ValidationError("Only active vehicles can be assigned to deliveries")
        
        return value
    
    def validate(self, attrs):
        """Cross-field validation"""
        driver = attrs.get('driver')
        vehicle = attrs.get('vehicle')
        status = attrs.get('status', 'in_process')
        
        if driver and vehicle:
            # Check if driver can handle the vehicle's driving category
            if not driver.can_handle_driving_category(vehicle.driving_category):
                raise serializers.ValidationError({
                    'driver': f"Driver cannot handle vehicles of category {vehicle.driving_category}"
                })
        
        if status == 'in_process':
            # Check if driver is already assigned to another in-process delivery
            if driver:
                existing_delivery = OrderDelivery.objects.filter(
                    driver=driver,
                    status='in_process'
                ).exclude(pk=self.instance.pk if self.instance else None)
                
                if existing_delivery.exists():
                    raise serializers.ValidationError({
                        'driver': "Driver is already assigned to another in-process delivery"
                    })
            
            # Check if vehicle is already assigned to another in-process delivery
            if vehicle:
                existing_delivery = OrderDelivery.objects.filter(
                    vehicle=vehicle,
                    status='in_process'
                ).exclude(pk=self.instance.pk if self.instance else None)
                
                if existing_delivery.exists():
                    raise serializers.ValidationError({
                        'vehicle': "Vehicle is already assigned to another in-process delivery"
                    })
        
        return attrs




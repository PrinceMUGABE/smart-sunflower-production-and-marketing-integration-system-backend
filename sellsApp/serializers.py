from rest_framework import serializers
from .models import Sell, SellPayment
from stockApp.models import HarvestStock
from userApp.models import CustomUser
from django.utils import timezone


class SellPaymentSerializer(serializers.ModelSerializer):
    """Serializer for sell payments."""
    paid_by_info = serializers.SerializerMethodField()
    
    class Meta:
        model = SellPayment
        fields = [
            'id', 'amount', 'payment_date', 'payment_method',
            'reference_number', 'notes', 'paid_by', 'paid_by_info', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_paid_by_info(self, obj):
        if obj.paid_by:
            return {
                'id': obj.paid_by.id,
                'phone_number': obj.paid_by.phone_number,
                'role': obj.paid_by.role
            }
        return None


class HarvestStockInfoSerializer(serializers.ModelSerializer):
    """Simplified harvest stock info for sell serializer."""
    harvest_date = serializers.DateField(source='harvest.harvest_date', read_only=True)
    quality_grade = serializers.CharField(source='harvest.get_quality_grade_display', read_only=True)
    moisture_content = serializers.DecimalField(source='harvest.moisture_content', max_digits=5, decimal_places=2, read_only=True)
    oil_content = serializers.DecimalField(source='harvest.oil_content', max_digits=5, decimal_places=2, read_only=True)
    location = serializers.SerializerMethodField()
    
    class Meta:
        model = HarvestStock
        fields = [
            'id', 'current_quantity', 'harvest_date', 'quality_grade',
            'moisture_content', 'oil_content', 'location'
        ]
    
    def get_location(self, obj):
        harvest = obj.harvest
        return f"{harvest.village}, {harvest.cell}, {harvest.sector}, {harvest.district}"


class UserInfoSerializer(serializers.ModelSerializer):
    """Simplified user info for farmer/buyer."""
    
    class Meta:
        model = CustomUser
        fields = ['id', 'phone_number', 'email', 'role']


class SellSerializer(serializers.ModelSerializer):
    """Main serializer for Sell model."""
    farmer_info = UserInfoSerializer(source='farmer', read_only=True)
    buyer_info = UserInfoSerializer(source='buyer', read_only=True)
    harvest_stock_info = HarvestStockInfoSerializer(source='harvest_stock', read_only=True)
    payments = SellPaymentSerializer(many=True, read_only=True)
    remaining_balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    harvest_info = serializers.ReadOnlyField()
    estimated_delivery_date = serializers.ReadOnlyField()
    days_until_delivery = serializers.ReadOnlyField()
    is_delivery_overdue = serializers.ReadOnlyField()
    
    class Meta:
        model = Sell
        fields = [
            'id', 'farmer', 'farmer_info', 'buyer', 'buyer_info', 'harvest_stock', 
            'harvest_stock_info', 'quantity_sold', 'unit_price', 'total_amount', 
            'delivery_days', 'buyer_name', 'buyer_phone', 'buyer_email', 'buyer_address', 
            'sell_status', 'payment_status', 'amount_paid', 'remaining_balance', 
            'delivery_date', 'delivery_address', 'delivery_notes', 'payment_completed_date',
            'estimated_delivery_date', 'days_until_delivery', 'is_delivery_overdue',
            'notes', 'purchased_date', 'created_at', 'updated_at', 
            'payments', 'harvest_info'
        ]
        read_only_fields = [
            'id', 'total_amount', 'payment_status', 'amount_paid', 'purchased_date',
            'created_at', 'updated_at', 'buyer_name', 'buyer_phone', 'buyer_email',
            'delivery_date', 'payment_completed_date'
        ]


class SellCreateSerializer(serializers.ModelSerializer):
    """Serializer for farmers creating sell posts."""
    
    class Meta:
        model = Sell
        fields = [
            'harvest_stock', 'quantity_sold', 'unit_price', 'delivery_days',
            'delivery_notes', 'notes'
        ]
    
    def validate_harvest_stock(self, value):
        """Validate that the harvest stock belongs to the logged-in farmer."""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            if value.harvest.farmer != request.user:
                raise serializers.ValidationError(
                    "You can only sell from your own harvest stock."
                )
        return value
    
    def validate_quantity_sold(self, value):
        """Validate sufficient stock quantity."""
        if value <= 0:
            raise serializers.ValidationError("Quantity sold must be greater than 0.")
        return value
    
    def validate_unit_price(self, value):
        """Validate unit price is positive."""
        if value <= 0:
            raise serializers.ValidationError("Unit price must be greater than 0.")
        return value
    
    def validate_delivery_days(self, value):
        """Validate delivery days is reasonable."""
        if value < 1:
            raise serializers.ValidationError("Delivery days must be at least 1 day.")
        if value > 365:
            raise serializers.ValidationError("Delivery days cannot exceed 365 days.")
        return value
    
    def validate(self, attrs):
        """Validate stock availability."""
        harvest_stock = attrs.get('harvest_stock')
        quantity_sold = attrs.get('quantity_sold')
        
        if harvest_stock and quantity_sold:
            if quantity_sold > harvest_stock.current_quantity:
                raise serializers.ValidationError(
                    f"Insufficient stock. Only {harvest_stock.current_quantity} kg available."
                )
        
        return attrs


class SellUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating sells (farmer only for posted items)."""
    
    class Meta:
        model = Sell
        fields = [
            'quantity_sold', 'unit_price', 'delivery_days', 'delivery_notes', 
            'notes', 'sell_status'
        ]
    
    def validate_sell_status(self, value):
        """Validate status transitions."""
        if self.instance:
            current_status = self.instance.sell_status
            # Only allow cancelling posted items
            if current_status == 'posted' and value not in ['posted', 'cancelled']:
                raise serializers.ValidationError(
                    "Can only cancel posted items. Buyers purchase items."
                )
            # Don't allow changing completed status
            if current_status == 'completed':
                raise serializers.ValidationError(
                    "Cannot modify completed sales."
                )
            # Don't allow changing purchased items back to posted
            if current_status in ['purchased', 'completed'] and value == 'posted':
                raise serializers.ValidationError(
                    "Cannot change purchased/completed items back to posted."
                )
        return value
    
    def validate_delivery_days(self, value):
        """Validate delivery days."""
        if value < 1:
            raise serializers.ValidationError("Delivery days must be at least 1 day.")
        if value > 365:
            raise serializers.ValidationError("Delivery days cannot exceed 365 days.")
        return value
    
    def validate(self, attrs):
        """Additional validation for updates."""
        if self.instance and self.instance.sell_status != 'posted':
            # Don't allow changing core details after purchase
            restricted_fields = ['quantity_sold', 'unit_price', 'delivery_days']
            for field in restricted_fields:
                if field in attrs and attrs[field] != getattr(self.instance, field):
                    raise serializers.ValidationError(
                        f"Cannot change {field} after item has been purchased."
                    )
        return attrs


class SellPurchaseSerializer(serializers.ModelSerializer):
    """Serializer for buyers purchasing posted items."""
    delivery_address = serializers.CharField(required=True, allow_blank=False)
    
    class Meta:
        model = Sell
        fields = ['delivery_address']
    
    def validate_delivery_address(self, value):
        """Validate delivery address is provided."""
        if not value or not value.strip():
            raise serializers.ValidationError("Delivery address is required for purchase.")
        return value.strip()
    
    def validate(self, attrs):
        """Validate purchase eligibility."""
        if self.instance.sell_status != 'posted':
            raise serializers.ValidationError(
                "This item is no longer available for purchase."
            )
        return attrs


class SellListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing sells."""
    farmer_phone = serializers.CharField(source='farmer.phone_number', read_only=True)
    buyer_phone = serializers.CharField(source='buyer.phone_number', read_only=True)
    harvest_grade = serializers.CharField(source='harvest_stock.harvest.get_quality_grade_display', read_only=True)
    harvest_location = serializers.SerializerMethodField()
    remaining_balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    estimated_delivery_date = serializers.ReadOnlyField()
    days_until_delivery = serializers.ReadOnlyField()
    is_delivery_overdue = serializers.ReadOnlyField()
    
    class Meta:
        model = Sell
        fields = [
            'id', 'farmer_phone', 'buyer_phone', 'harvest_grade', 'harvest_location',
            'quantity_sold', 'unit_price', 'total_amount', 'delivery_days', 'sell_status',
            'payment_status', 'remaining_balance', 'estimated_delivery_date', 
            'days_until_delivery', 'is_delivery_overdue', 'purchased_date', 
            'created_at'
        ]
    
    def get_harvest_location(self, obj):
        harvest = obj.harvest_stock.harvest
        return f"{harvest.district}, {harvest.sector}"


class AvailableSellSerializer(serializers.ModelSerializer):
    """Serializer for available sells that buyers can view and purchase."""
    farmer_info = UserInfoSerializer(source='farmer', read_only=True)
    harvest_stock_info = HarvestStockInfoSerializer(source='harvest_stock', read_only=True)
    harvest_info = serializers.ReadOnlyField()
    
    class Meta:
        model = Sell
        fields = [
            'id', 'farmer_info', 'harvest_stock_info', 'quantity_sold', 
            'unit_price', 'total_amount', 'delivery_days', 'delivery_notes', 
            'notes', 'created_at', 'harvest_info'
        ]


class PaymentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating payments."""
    
    class Meta:
        model = SellPayment
        fields = [
            'sell', 'amount', 'payment_date', 'payment_method',
            'reference_number', 'notes'
        ]
    
    def validate_sell(self, value):
        """Validate payment eligibility."""
        request = self.context.get('request')
        user = request.user if request else None
        
        # Check if user has permission to make payment
        if user:
            if user.role == 'buyer' and value.buyer != user:
                raise serializers.ValidationError(
                    "You can only make payments for your own purchases."
                )
            elif user.role == 'farmer' and value.farmer != user:
                raise serializers.ValidationError(
                    "Farmers can only make payments for their own sells."
                )
        
        # Check if sell is in purchasable state
        if value.sell_status not in ['purchased', 'completed']:
            raise serializers.ValidationError(
                "Can only make payments for purchased items."
            )
        
        return value
    
    def validate_amount(self, value):
        """Validate payment amount."""
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be greater than 0.")
        return value
    
    def validate(self, attrs):
        """Validate payment against remaining balance."""
        sell = attrs.get('sell')
        amount = attrs.get('amount')
        
        if sell and amount:
            if amount > sell.remaining_balance:
                raise serializers.ValidationError(
                    f"Payment amount ({amount}) exceeds remaining balance ({sell.remaining_balance})."
                )
        
        return attrs
    
    def create(self, validated_data):
        """Create payment and set paid_by."""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['paid_by'] = request.user
        return super().create(validated_data)


class DeliveryUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating delivery information."""
    
    class Meta:
        model = Sell
        fields = ['delivery_address', 'delivery_notes']
    
    def validate_delivery_address(self, value):
        """Validate delivery address."""
        if not value or not value.strip():
            raise serializers.ValidationError("Delivery address cannot be empty.")
        return value.strip()
    
    def validate(self, attrs):
        """Validate delivery update eligibility."""
        if self.instance.sell_status not in ['purchased', 'completed']:
            raise serializers.ValidationError(
                "Can only update delivery information for purchased items."
            )
        return attrs
# purchaseApp/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from sellsApp.models import Sell
from .models import Purchase, PurchasePayment

User = get_user_model()


class FarmerInfoSerializer(serializers.Serializer):
    """Serializer for farmer information."""
    id = serializers.IntegerField()
    phone_number = serializers.CharField()
    email = serializers.EmailField(allow_blank=True)


class HarvestInfoSerializer(serializers.Serializer):
    """Serializer for harvest information."""
    harvest_date = serializers.DateField()
    quality_grade = serializers.CharField()
    moisture_content = serializers.DecimalField(max_digits=5, decimal_places=2)
    oil_content = serializers.DecimalField(max_digits=5, decimal_places=2)
    location = serializers.CharField()


class SellInfoSerializer(serializers.ModelSerializer):
    """Serializer for sell information in purchase."""
    farmer_info = FarmerInfoSerializer(source='*', read_only=True)
    harvest_info = HarvestInfoSerializer(source='*', read_only=True)
    
    class Meta:
        model = Sell
        fields = [
            'id', 'quantity_sold', 'unit_price', 'total_amount',
            'delivery_days', 'sell_status', 'payment_status',
            'sell_date', 'created_at', 'farmer_info', 'harvest_info'
        ]
        read_only_fields = fields


class PurchasePaymentSerializer(serializers.ModelSerializer):
    """Serializer for purchase payments."""
    
    class Meta:
        model = PurchasePayment
        fields = [
            'id', 'amount', 'payment_method', 'paypack_ref',
            'paypack_status', 'phone_number', 'status',
            'reference_number', 'transaction_date', 'completed_date',
            'notes', 'failure_reason'
        ]
        read_only_fields = [
            'id', 'paypack_ref', 'paypack_status', 'status',
            'transaction_date', 'completed_date'
        ]


class PurchaseSerializer(serializers.ModelSerializer):
    """Serializer for purchases with full related data."""
    sell_info = SellInfoSerializer(source='sell', read_only=True)
    payments = PurchasePaymentSerializer(many=True, read_only=True)
    farmer_info = serializers.ReadOnlyField()
    harvest_info = serializers.ReadOnlyField()
    remaining_balance = serializers.ReadOnlyField()
    payment_progress = serializers.ReadOnlyField()
    can_make_payment = serializers.ReadOnlyField()
    buyer_name = serializers.CharField(source='buyer.phone_number', read_only=True)
    
    class Meta:
        model = Purchase
        fields = [
            'id', 'buyer', 'buyer_name', 'sell', 'quantity_purchased',
            'unit_price', 'total_amount', 'amount_paid', 'delivery_address',
            'delivery_notes', 'expected_delivery_date', 'actual_delivery_date',
            'purchase_status', 'purchased_date', 'updated_at',
            'completed_payment_date', 'notes', 'remaining_balance',
            'payment_progress', 'can_make_payment', 'sell_info',
            'payments', 'farmer_info', 'harvest_info'
        ]
        read_only_fields = [
            'id', 'buyer', 'quantity_purchased', 'unit_price', 'total_amount',
            'purchased_date', 'updated_at', 'completed_payment_date',
            'expected_delivery_date', 'purchase_status'
        ]


class PurchaseCreateSerializer(serializers.Serializer):
    """Serializer for creating a purchase."""
    sell_id = serializers.IntegerField()
    delivery_address = serializers.CharField(max_length=500)
    delivery_notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    
    def validate_sell_id(self, value):
        """Validate that sell exists and is available."""
        try:
            sell = Sell.objects.get(id=value)
        except Sell.DoesNotExist:
            raise serializers.ValidationError("Sell not found")
        
        if sell.sell_status != 'posted':
            raise serializers.ValidationError("This sell is no longer available for purchase")
        
        # Check if sell already has a purchase
        if hasattr(sell, 'purchase'):
            raise serializers.ValidationError("This sell has already been purchased")
        
        return value
    
    def validate_delivery_address(self, value):
        """Validate delivery address."""
        if not value.strip():
            raise serializers.ValidationError("Delivery address is required")
        return value.strip()


class PurchaseUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating purchase details."""
    
    class Meta:
        model = Purchase
        fields = [
            'delivery_address', 'delivery_notes', 'notes',
            'actual_delivery_date'
        ]
    
    def validate(self, data):
        """Validate update data."""
        purchase = self.instance
        
        # Don't allow updates if purchase is delivered or cancelled
        if purchase.purchase_status in ['delivered', 'cancelled']:
            raise serializers.ValidationError(
                "Cannot update delivered or cancelled purchases"
            )
        
        return data


class PaymentCreateSerializer(serializers.Serializer):
    """Serializer for creating a payment."""
    purchase_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    phone_number = serializers.CharField(max_length=15)
    payment_method = serializers.ChoiceField(
        choices=PurchasePayment.PAYMENT_METHOD_CHOICES,
        default='paypack'
    )
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    def validate_purchase_id(self, value):
        """Validate that purchase exists and can accept payments."""
        try:
            purchase = Purchase.objects.get(id=value)
        except Purchase.DoesNotExist:
            raise serializers.ValidationError("Purchase not found")
        
        if not purchase.can_make_payment:
            raise serializers.ValidationError(
                "This purchase cannot accept more payments"
            )
        
        return value
    
    def validate_amount(self, value):
        """Validate payment amount."""
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be greater than 0")
        return value
    
    def validate_phone_number(self, value):
        """Validate phone number format."""
        # Remove any spaces or special characters
        phone = ''.join(filter(str.isdigit, value))
        
        # Rwanda phone number validation (should start with 078, 079, 072, 073)
        if not phone.startswith(('078', '079', '072', '073')):
            raise serializers.ValidationError(
                "Invalid phone number format. Must be a valid Rwandan number"
            )
        
        if len(phone) != 10:
            raise serializers.ValidationError(
                "Phone number must be 10 digits"
            )
        
        return phone
    
    def validate(self, data):
        """Cross-field validation."""
        try:
            purchase = Purchase.objects.get(id=data['purchase_id'])
            
            # Check if payment amount exceeds remaining balance
            if data['amount'] > purchase.remaining_balance:
                raise serializers.ValidationError({
                    'amount': f"Payment amount cannot exceed remaining balance of {purchase.remaining_balance}"
                })
            
        except Purchase.DoesNotExist:
            pass  # Will be caught by purchase_id validation
        
        return data


class PurchaseStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating purchase status."""
    status = serializers.ChoiceField(choices=Purchase.PURCHASE_STATUS_CHOICES)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    def validate_status(self, value):
        """Validate status transition."""
        purchase = self.context.get('purchase')
        if not purchase:
            return value
        
        current_status = purchase.purchase_status
        
        # Define allowed status transitions
        allowed_transitions = {
            'pending_payment': ['partially_paid', 'cancelled'],
            'partially_paid': ['fully_paid', 'cancelled'],
            'fully_paid': ['delivered', 'cancelled'],
            'delivered': [],  # Final status
            'cancelled': []   # Final status
        }
        
        if value not in allowed_transitions.get(current_status, []):
            raise serializers.ValidationError(
                f"Cannot change status from {current_status} to {value}"
            )
        
        # Additional validations
        if value == 'delivered' and current_status != 'fully_paid':
            raise serializers.ValidationError(
                "Can only mark as delivered when fully paid"
            )
        
        return value
# purchaseApp/models.py
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.utils import timezone
from userApp.models import CustomUser
from sellsApp.models import Sell


class Purchase(models.Model):
    """Manages purchases made by buyers with payment tracking."""
    PURCHASE_STATUS_CHOICES = [
        ('pending_payment', 'Pending Payment'),
        ('partially_paid', 'Partially Paid'),
        ('fully_paid', 'Fully Paid'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled')
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded')
    ]

    # Purchase information
    buyer = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='purchases',
        limit_choices_to={'role': 'buyer'}
    )
    sell = models.OneToOneField(
        Sell,
        on_delete=models.CASCADE,
        related_name='purchase'
    )
    
    # Purchase details
    quantity_purchased = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Quantity purchased in kilograms"
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Price per kilogram"
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Total purchase amount"
    )
    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Delivery information
    delivery_address = models.TextField(help_text="Buyer's delivery address")
    delivery_notes = models.TextField(blank=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateField(null=True, blank=True)
    
    # Status tracking
    purchase_status = models.CharField(
        max_length=20,
        choices=PURCHASE_STATUS_CHOICES,
        default='pending_payment'
    )
    
    # Timestamps
    purchased_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_payment_date = models.DateTimeField(null=True, blank=True)
    
    # Additional information
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-purchased_date']
        
    def clean(self):
        """Validate purchase data."""
        # Ensure buyer is actually a buyer
        if self.buyer.role != 'buyer':
            raise ValidationError("Only buyers can make purchases")
            
        # Ensure sell is available for purchase
        if self.sell.sell_status != 'posted':
            raise ValidationError("This sell is no longer available for purchase")
            
        # Validate quantities match
        if self.quantity_purchased != self.sell.quantity_sold:
            raise ValidationError("Purchase quantity must match sell quantity")
            
        # Validate prices match
        if self.unit_price != self.sell.unit_price:
            raise ValidationError("Purchase price must match sell price")
            
        # Validate payment amount
        if self.amount_paid > self.total_amount:
            raise ValidationError("Amount paid cannot exceed total amount")
    
    def save(self, *args, **kwargs):
        """Calculate total amount and update sell status."""
        # Calculate total amount
        self.total_amount = self.quantity_purchased * self.unit_price
        
        # Update purchase status based on payment
        if self.amount_paid == 0:
            self.purchase_status = 'pending_payment'
        elif self.amount_paid >= self.total_amount:
            self.purchase_status = 'fully_paid'
            if not self.completed_payment_date:
                self.completed_payment_date = timezone.now()
        else:
            self.purchase_status = 'partially_paid'
        
        # Calculate expected delivery date
        if self.purchase_status == 'fully_paid' and not self.expected_delivery_date:
            self.expected_delivery_date = (
                self.completed_payment_date.date() + 
                timezone.timedelta(days=self.sell.delivery_days)
            )
        
        super().save(*args, **kwargs)
        
        # Update the associated sell
        self._update_sell_status()
    
    def _update_sell_status(self):
        """Update the associated sell status based on purchase."""
        self.sell.buyer = self.buyer
        self.sell.sell_status = 'purchased'
        self.sell.amount_paid = self.amount_paid
        self.sell.delivery_address = self.delivery_address
        self.sell.purchased_date = self.purchased_date
        
        # Update sell payment status
        if self.purchase_status == 'fully_paid':
            self.sell.payment_status = 'paid'
            self.sell.payment_completed_date = self.completed_payment_date
            self.sell.delivery_date = self.expected_delivery_date
        elif self.purchase_status == 'partially_paid':
            self.sell.payment_status = 'partial'
        else:
            self.sell.payment_status = 'unpaid'
            
        self.sell.save()
    
    @property
    def remaining_balance(self):
        """Calculate remaining balance."""
        return self.total_amount - self.amount_paid
    
    @property
    def payment_progress(self):
        """Calculate payment progress percentage."""
        if self.total_amount > 0:
            return (self.amount_paid / self.total_amount) * 100
        return 0
    
    @property
    def can_make_payment(self):
        """Check if buyer can still make payments."""
        return (
            self.purchase_status in ['pending_payment', 'partially_paid'] and
            self.remaining_balance > 0
        )
    
    @property
    def farmer_info(self):
        """Get farmer information."""
        return {
            'id': self.sell.farmer.id,
            'phone_number': self.sell.farmer.phone_number,
            'email': self.sell.farmer.email
        }
    
    @property
    def harvest_info(self):
        """Get harvest information."""
        return self.sell.harvest_info
    
    def __str__(self):
        return f"Purchase #{self.id} - {self.buyer.phone_number} bought {self.quantity_purchased}kg"


class PurchasePayment(models.Model):
    """Track individual payments for a purchase."""
    PAYMENT_METHOD_CHOICES = [
        ('paypack', 'PayPack Mobile Money'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('other', 'Other')
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled')
    ]
    
    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    payment_method = models.CharField(
        max_length=50,
        choices=PAYMENT_METHOD_CHOICES,
        default='paypack'
    )
    
    # PayPack specific fields
    paypack_ref = models.CharField(max_length=100, blank=True, null=True)
    paypack_status = models.CharField(max_length=20, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True)
    
    # Payment tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    reference_number = models.CharField(max_length=100, blank=True)
    transaction_date = models.DateTimeField(auto_now_add=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    
    # Additional information
    notes = models.TextField(blank=True)
    failure_reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-transaction_date']
    
    def clean(self):
        """Validate payment doesn't exceed remaining balance."""
        if not self.purchase.can_make_payment:
            raise ValidationError("Cannot make payment for this purchase")
            
        current_payments = self.purchase.payments.filter(
            status='completed'
        ).exclude(pk=self.pk).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        
        if (current_payments + self.amount) > self.purchase.total_amount:
            raise ValidationError("Payment exceeds remaining balance")
    
    def save(self, *args, **kwargs):
        """Update purchase amount_paid when payment is completed."""
        is_new = self.pk is None
        old_status = None
        
        if not is_new:
            try:
                old_payment = PurchasePayment.objects.get(pk=self.pk)
                old_status = old_payment.status
            except PurchasePayment.DoesNotExist:
                pass
        
        # Set completion date when status changes to completed
        if self.status == 'completed' and old_status != 'completed':
            self.completed_date = timezone.now()
        
        super().save(*args, **kwargs)
        
        # Update purchase amount_paid only for completed payments
        if self.status == 'completed':
            total_completed_payments = self.purchase.payments.filter(
                status='completed'
            ).aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0.00')
            
            self.purchase.amount_paid = total_completed_payments
            self.purchase.save()
    
    def __str__(self):
        return f"Payment of {self.amount} for Purchase #{self.purchase.id} - {self.status}"
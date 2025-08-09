from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import timedelta
from userApp.models import CustomUser
from stockApp.models import HarvestStock, HarvestMovement


class Sell(models.Model):
    """Manages stock sales for farmers with buyer integration."""
    SELL_STATUS_CHOICES = [
        ('posted', 'Posted for Sale'),      # Farmer posted, no buyer yet
        ('purchased', 'Purchased'),         # Buyer has claimed the sale
        ('completed', 'Completed'),         # Sale completed with delivery
        ('cancelled', 'Cancelled')          # Sale cancelled
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Fully Paid')
    ]
    
    # Basic sell information
    farmer = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='farmer_sells',
        limit_choices_to={'role': 'farmer'}
    )
    harvest_stock = models.ForeignKey(
        HarvestStock,
        on_delete=models.CASCADE,
        related_name='sells'
    )
    
    # Buyer information - can be null initially when farmer posts
    buyer = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='buyer_purchases',
        limit_choices_to={'role': 'buyer'}
    )
    
    # Sell details
    quantity_sold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Quantity available for sale in kilograms"
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
        editable=False,
        help_text="Total amount (calculated automatically)"
    )
    
    # Delivery configuration
    delivery_days = models.PositiveIntegerField(
        default=7,
        validators=[MinValueValidator(1)],
        help_text="Number of days for delivery after full payment"
    )
    
    # Legacy buyer fields for backward compatibility or manual buyer info
    buyer_name = models.CharField(max_length=200, blank=True)
    buyer_phone = models.CharField(max_length=15, blank=True)
    buyer_email = models.EmailField(blank=True, null=True)
    buyer_address = models.TextField(blank=True)
    
    # Sale status and payment
    sell_status = models.CharField(
        max_length=20,
        choices=SELL_STATUS_CHOICES,
        default='posted'
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='unpaid'
    )
    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Delivery information - No default delivery address
    delivery_date = models.DateField(null=True, blank=True, help_text="Calculated delivery date")
    delivery_address = models.TextField(blank=True, help_text="Set by buyer during purchase")
    delivery_notes = models.TextField(blank=True)
    
    # Payment completion tracking
    payment_completed_date = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Date when full payment was completed"
    )
    
    # Additional information
    notes = models.TextField(blank=True)
    sell_date = models.DateField(null=True, blank=True)
    purchased_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def clean(self):
        """Validate sell data."""
        # Check if farmer owns the harvest stock
        if self.harvest_stock.harvest.farmer != self.farmer:
            raise ValidationError("Farmer can only sell from their own harvest stock")
            
        # Check sufficient stock
        if self.quantity_sold > self.harvest_stock.current_quantity:
            raise ValidationError(
                f"Insufficient stock. Only {self.harvest_stock.current_quantity} kg available."
            )
            
        # Validate payment amount
        if self.amount_paid > self.total_amount:
            raise ValidationError("Amount paid cannot exceed total amount")
            
        # Validate buyer assignment for purchased status
        if self.sell_status in ['purchased', 'completed'] and not self.buyer:
            if not all([self.buyer_name, self.buyer_phone]):
                raise ValidationError(
                    "Buyer information is required for purchased/completed sales"
                )
        
        # Validate delivery days
        if self.delivery_days < 1:
            raise ValidationError("Delivery days must be at least 1 day")
    
    def calculate_delivery_date(self):
        """Calculate delivery date based on payment completion date and delivery days."""
        if self.payment_completed_date:
            return self.payment_completed_date.date() + timedelta(days=self.delivery_days)
        return None
    
    def update_payment_completion(self):
        """Update payment completion date and delivery date when fully paid."""
        from django.utils import timezone
        
        if self.payment_status == 'paid' and not self.payment_completed_date:
            self.payment_completed_date = timezone.now()
            self.delivery_date = self.calculate_delivery_date()
    
    def save(self, *args, **kwargs):
        """Calculate total amount and update stock on completion."""
        # Calculate total amount
        self.total_amount = self.quantity_sold * self.unit_price
        
        # Update payment status based on amount paid
        old_payment_status = None
        if self.pk:
            try:
                old_sell = Sell.objects.get(pk=self.pk)
                old_payment_status = old_sell.payment_status
            except Sell.DoesNotExist:
                pass
        
        if self.amount_paid == 0:
            self.payment_status = 'unpaid'
        elif self.amount_paid >= self.total_amount:
            self.payment_status = 'paid'
            # Update payment completion date and delivery date if status changed to paid
            if old_payment_status != 'paid':
                self.update_payment_completion()
        else:
            self.payment_status = 'partial'
        
        # Auto-fill buyer info from CustomUser if buyer is assigned
        if self.buyer:
            self.buyer_name = f"{self.buyer.phone_number}"
            self.buyer_phone = self.buyer.phone_number
            self.buyer_email = self.buyer.email or ""
        
        is_new = self.pk is None
        old_status = None
        
        if not is_new:
            try:
                old_sell = Sell.objects.get(pk=self.pk)
                old_status = old_sell.sell_status
            except Sell.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
        # Create stock movement when sell is completed (only once)
        if (self.sell_status == 'completed' and 
            (is_new or old_status != 'completed')):
            self._create_stock_movement()
    
    def _create_stock_movement(self):
        """Create stock movement for completed sell."""
        try:
            buyer_info = self.buyer.phone_number if self.buyer else self.buyer_name
            HarvestMovement.objects.create(
                stock=self.harvest_stock,
                movement_type='out',
                quantity=self.quantity_sold,
                notes=f"Stock sold to {buyer_info} - Sell ID: {self.id}",
                created_by=self.farmer
            )
        except Exception as e:
            print(f"Error creating stock movement for sell {self.id}: {str(e)}")
    
    def purchase_by_buyer(self, buyer_user, delivery_address):
        """Method to handle buyer purchasing this sell."""
        if self.sell_status != 'posted':
            raise ValidationError("This item is no longer available for purchase")
        
        if buyer_user.role != 'buyer':
            raise ValidationError("Only buyers can purchase items")
        
        if not delivery_address:
            raise ValidationError("Delivery address is required for purchase")
        
        from django.utils import timezone
        
        self.buyer = buyer_user
        self.sell_status = 'purchased'
        self.purchased_date = timezone.now()
        self.delivery_address = delivery_address
        self.save()
    
    @property
    def remaining_balance(self):
        """Calculate remaining balance."""
        return self.total_amount - self.amount_paid
    
    @property
    def estimated_delivery_date(self):
        """Get estimated delivery date."""
        if self.delivery_date:
            return self.delivery_date
        elif self.payment_completed_date:
            return self.calculate_delivery_date()
        elif self.purchased_date and self.payment_status == 'paid':
            return self.purchased_date.date() + timedelta(days=self.delivery_days)
        return None
    
    @property
    def days_until_delivery(self):
        """Calculate days until delivery from today."""
        if self.estimated_delivery_date:
            from django.utils import timezone
            today = timezone.now().date()
            delta = self.estimated_delivery_date - today
            return delta.days
        return None
    
    @property
    def is_delivery_overdue(self):
        """Check if delivery is overdue."""
        days_until = self.days_until_delivery
        return days_until is not None and days_until < 0
    
    @property
    def harvest_info(self):
        """Get harvest information."""
        return {
            'harvest_date': self.harvest_stock.harvest.harvest_date,
            'quality_grade': self.harvest_stock.harvest.get_quality_grade_display(),
            'moisture_content': self.harvest_stock.harvest.moisture_content,
            'oil_content': self.harvest_stock.harvest.oil_content,
            'location': f"{self.harvest_stock.harvest.village}, {self.harvest_stock.harvest.cell}, {self.harvest_stock.harvest.sector}, {self.harvest_stock.harvest.district}"
        }
    
    @property
    def buyer_info(self):
        """Get buyer information."""
        if self.buyer:
            return {
                'id': self.buyer.id,
                'phone_number': self.buyer.phone_number,
                'email': self.buyer.email
            }
        elif self.buyer_name:
            return {
                'name': self.buyer_name,
                'phone': self.buyer_phone,
                'email': self.buyer_email
            }
        return None
    
    def __str__(self):
        buyer_info = self.buyer.phone_number if self.buyer else self.buyer_name or "No Buyer"
        return f"Sell #{self.id} - {self.quantity_sold}kg to {buyer_info}"


class SellPayment(models.Model):
    """Track individual payments for a sell."""
    sell = models.ForeignKey(
        Sell,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    payment_date = models.DateField()
    payment_method = models.CharField(
        max_length=50,
        choices=[
            ('cash', 'Cash'),
            ('bank_transfer', 'Bank Transfer'),
            ('mobile_money', 'Mobile Money'),
            ('check', 'Check'),
            ('other', 'Other')
        ]
    )
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    # Track who made the payment (buyer or on behalf)
    paid_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments_made'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-payment_date']
    
    def clean(self):
        """Validate payment doesn't exceed remaining balance."""
        current_payments = self.sell.payments.exclude(pk=self.pk).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        
        if (current_payments + self.amount) > self.sell.total_amount:
            raise ValidationError("Payment exceeds remaining balance")
    
    def save(self, *args, **kwargs):
        """Update sell's amount_paid and payment status after saving payment."""
        is_new = self.pk is None
        
        super().save(*args, **kwargs)
        
        # Recalculate total payments for the sell
        total_payments = self.sell.payments.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        
        old_payment_status = self.sell.payment_status
        self.sell.amount_paid = total_payments
        
        # Auto-update payment status when total amount is paid
        if total_payments >= self.sell.total_amount:
            self.sell.payment_status = 'paid'
            # Update payment completion date if status changed to paid
            if old_payment_status != 'paid':
                self.sell.update_payment_completion()
        elif total_payments > 0:
            self.sell.payment_status = 'partial'
        else:
            self.sell.payment_status = 'unpaid'
            
        self.sell.save()
    
    def __str__(self):
        return f"Payment of {self.amount} for Sell #{self.sell.id}"
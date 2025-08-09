from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal
from userApp.models import CustomUser


from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from userApp.models import CustomUser


class Stock(models.Model):
    """Single model for managing stock and product movements"""
    
    # Movement types
    MOVEMENT_TYPES = [
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
        ('adjustment', 'Adjustment'),
        ('transfer', 'Transfer'),
    ]
    
    
    SALE_STATUS = [
        ('on_sell', 'On Sell'),
        ('not_on_sell', 'Not On Sell'),
    ]
    

    
    # Basic product information
    category = models.CharField(max_length=100, blank=True)
    unit_of_measurement = models.CharField(max_length=20, default='kg')

    
    # Stock location
    district = models.CharField(max_length=100, help_text="district location of the stock")
    sector = models.CharField(max_length=100, help_text="sector location of the stock")
    sell_status = models.CharField(max_length=10, choices=SALE_STATUS, blank=True)
    
    # Quantity management
    current_quantity = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Current stock quantity"
    )
    
    # Optional: Set minimum stock level for alerts
    minimum_stock_level = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Minimum stock level for alerts"
    )
    
    # Movement tracking fields
    last_movement_type = models.CharField(max_length=10, choices=MOVEMENT_TYPES, blank=True)
    last_movement_quantity = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Last movement quantity"
    )
    last_movement_date = models.DateTimeField(blank=True, null=True)
    last_movement_reference = models.CharField(max_length=50, blank=True)
    last_movement_notes = models.TextField(blank=True)
    
    # User tracking
    owner = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='stocks',
        help_text="Stock owner"
    )
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['product_name', 'location', 'owner']
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['owner', 'product_name']),
            models.Index(fields=['owner', 'location']),
        ]
    
    def __str__(self):
        return f"{self.district} ({self.sector}) - {self.current_quantity} {self.unit_of_measurement}"
    
    def clean(self):
        """Validate stock data"""
        if self.current_quantity < 0:
            raise ValidationError("Stock quantity cannot be negative")
    
    def save(self, *args, **kwargs):
        """Override save to validate data"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    # Stock management methods
    def add_stock(self, quantity, reference_number="", notes="", user=None):
        """Add stock (Stock In movement)"""
        quantity = Decimal(str(quantity))
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        self.current_quantity += quantity
        self._record_movement('in', quantity, reference_number, notes, user)
        self.save()
        return True
    
    def remove_stock(self, quantity, reference_number="", notes="", user=None):
        """Remove stock (Stock Out movement)"""
        quantity = Decimal(str(quantity))
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        if quantity > self.current_quantity:
            raise ValueError(f"Insufficient stock. Available: {self.current_quantity}")
        
        self.current_quantity -= quantity
        self._record_movement('out', quantity, reference_number, notes, user)
        self.save()
        return True
    
    def adjust_stock(self, new_quantity, reference_number="", notes="", user=None):
        """Adjust stock to a specific quantity"""
        new_quantity = Decimal(str(new_quantity))
        if new_quantity < 0:
            raise ValueError("New quantity cannot be negative")
        
        adjustment = new_quantity - self.current_quantity
        self.current_quantity = new_quantity
        self._record_movement('adjustment', adjustment, reference_number, notes, user)
        self.save()
        return True
    
    def transfer_stock(self, target_stock, quantity, reference_number="", notes="", user=None):
        """Transfer stock to another stock record"""
        quantity = Decimal(str(quantity))
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        if quantity > self.current_quantity:
            raise ValueError(f"Insufficient stock. Available: {self.current_quantity}")
        
        # Remove from current stock
        self.current_quantity -= quantity
        self._record_movement('transfer', -quantity, reference_number, 
                            f"Transfer to {target_stock.district}: {notes}", user)
        
        # Add to target stock
        target_stock.current_quantity += quantity
        target_stock._record_movement('transfer', quantity, reference_number, 
                                    f"Transfer from {self.district}: {notes}", user)
        
        self.save()
        target_stock.save()
        return True
    
    def _record_movement(self, movement_type, quantity, reference_number, notes, user):
        """Internal method to record movement details"""
        self.last_movement_type = movement_type
        self.last_movement_quantity = abs(quantity)
        self.last_movement_date = timezone.now()
        self.last_movement_reference = reference_number
        self.last_movement_notes = notes
    
    # Stock status methods
    def is_low_stock(self):
        """Check if stock is below minimum level"""
        return self.current_quantity <= self.minimum_stock_level
    
    def get_stock_status(self):
        """Get current stock status"""
        if self.current_quantity == 0:
            return "Out of Stock"
        elif self.is_low_stock():
            return "Low Stock"
        else:
            return "In Stock"
    
    def get_stock_value_info(self):
        """Get stock information as dictionary"""
        return {
            'category': self.category,
            'district': self.district,
            'sector': self.sector,
            'current_quantity': float(self.current_quantity),
            'unit': self.unit_of_measurement,
            'minimum_level': float(self.minimum_stock_level),
            'status': self.get_stock_status(),
            'is_low_stock': self.is_low_stock(),
            'last_movement': {
                'type': self.last_movement_type,
                'quantity': float(self.last_movement_quantity) if self.last_movement_quantity else 0,
                'date': self.last_movement_date,
                'reference': self.last_movement_reference,
                'notes': self.last_movement_notes,
            }
        }
    
    # Class methods for user-specific queries
    @classmethod
    def get_user_stocks(cls, user):
        """Get all stocks for a specific user"""
        return cls.objects.filter(owner=user)
    
    @classmethod
    def get_low_stock_items(cls, user):
        """Get all low stock items for a user"""
        return cls.objects.filter(
            owner=user,
            current_quantity__lte=models.F('minimum_stock_level')
        )
    
    @classmethod
    def get_out_of_stock_items(cls, user):
        """Get all out of stock items for a user"""
        return cls.objects.filter(owner=user, current_quantity=0)
    
    @classmethod
    def get_stocks_by_category(cls, user, category):
        """Get stocks by category for a user"""
        return cls.objects.filter(owner=user, category__icontains=category)
    
    @classmethod
    def get_stocks_by_district(cls, user, district):
        """Get stocks by location for a user"""
        return cls.objects.filter(owner=user, location__icontains=district)
    
    
    @classmethod
    def get_stocks_by_sector(cls, user, sector):
        """Get stocks by sector for a user"""
        return cls.objects.filter(owner=user, sector__icontains=sector)



class StockMovementHistory(models.Model):
    """Detailed history of all stock movements (optional for detailed tracking)"""
    
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='movement_history')
    movement_type = models.CharField(max_length=10, choices=Stock.MOVEMENT_TYPES)
    quantity = models.DecimalField(max_digits=15, decimal_places=2)
    quantity_before = models.DecimalField(max_digits=15, decimal_places=2)
    quantity_after = models.DecimalField(max_digits=15, decimal_places=2)
    reference_number = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.movement_type}: {self.quantity} ({self.created_at})"
    
    
    

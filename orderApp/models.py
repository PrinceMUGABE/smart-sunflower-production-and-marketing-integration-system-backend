# models.py - Add this to your existing models file

from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from userApp.models import CustomUser
from django.db import transaction
from warehouseApp.models import Warehouse, Category, Commodity, WarehouseCommodity
from warehouseApp.models import InventoryMovement
from stockApp.models import StorageCost


class Order(models.Model):
    """Order model for managing warehouse commodity records"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
    ]
    
    AVAILABILITY_STATUS_CHOICES = [
        ('waiting', 'Waiting'),
        ('imported', 'Imported'),
        ('exported', 'Exported'),
    ]
    
    # Basic order information
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='orders')
    origin = models.CharField(max_length=200, help_text="Where the package is coming from")
    cost_charged = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Cost charged for this order"
    )
    
    # Status fields
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    availability_status = models.CharField(
        max_length=10, 
        choices=AVAILABILITY_STATUS_CHOICES, 
        default='waiting'
    )
    
    # Warehouse and commodity information
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='orders')
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE, related_name='orders')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='orders')
    quantity = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Quantity of commodity to be stored"
    )
    
    phone_number = models.CharField(
        max_length=20, 
        help_text="Phone number used for payment",
        blank=True
    )
    
    
    is_paid = models.BooleanField(
        default=False, 
        help_text="Whether the order has been paid for"
    )
    

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Reference to inventory movement (will be created when order is processed)
    inventory_movement = models.ForeignKey(InventoryMovement, on_delete=models.SET_NULL, 
                                         null=True, blank=True, related_name='order')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Order"
        verbose_name_plural = "Orders"
    
    def __str__(self):
        return f"Order #{self.id} - {self.commodity.name} ({self.quantity} {self.commodity.unit_of_measurement}) - {self.status}"
    
    def clean(self):
        """Validate order data"""
        errors = {}
        
        # Validate that commodity belongs to the specified category
        if self.commodity and self.category and self.commodity.category != self.category:
            errors['commodity'] = "Selected commodity does not belong to the specified category"
        
        # Validate warehouse capacity
        if self.warehouse and self.commodity and self.quantity:
            try:
                warehouse_commodity = WarehouseCommodity.objects.get(
                    warehouse=self.warehouse,
                    commodity=self.commodity
                )
                if not warehouse_commodity.can_add_quantity(self.quantity):
                    available_capacity = warehouse_commodity.get_available_capacity()
                    errors['quantity'] = f"Insufficient warehouse capacity. Available: {available_capacity} {self.commodity.unit_of_measurement}"
            except WarehouseCommodity.DoesNotExist:
                errors['warehouse'] = "This warehouse doesn't support the selected commodity"
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Override save to auto-assign driver and vehicle"""
        is_new = self.pk is None
        
        # Validate before saving
        self.full_clean()
        
        
        super().save(*args, **kwargs)
    

    def get_available_warehouse_capacity(self):
        """Get available capacity for this commodity in the warehouse"""
        try:
            warehouse_commodity = WarehouseCommodity.objects.get(
                warehouse=self.warehouse,
                commodity=self.commodity
            )
            return warehouse_commodity.get_available_capacity()
        except WarehouseCommodity.DoesNotExist:
            return 0
    
    def can_be_stored(self):
        """Check if this order can be stored in the warehouse"""
        try:
            warehouse_commodity = WarehouseCommodity.objects.get(
                warehouse=self.warehouse,
                commodity=self.commodity
            )
            return warehouse_commodity.can_add_quantity(self.quantity)
        except WarehouseCommodity.DoesNotExist:
            return False
    
    @transaction.atomic
    def confirm_order(self):
        """Confirm the order and update inventory"""
        if self.status != 'pending':
            raise ValidationError("Only pending orders can be confirmed")
        
        # Check if order can still be stored
        if not self.can_be_stored():
            raise ValidationError("Insufficient warehouse capacity to confirm this order")
        
        # Get or create warehouse commodity
        warehouse_commodity, created = WarehouseCommodity.objects.get_or_create(
            warehouse=self.warehouse,
            commodity=self.commodity,
            defaults={
                'max_capacity': self.quantity * 10,  # Set default max capacity
                'created_by': self.user
            }
        )
        
        # Add quantity to warehouse
        if warehouse_commodity.add_quantity(self.quantity):
            # Create inventory movement record
            movement = InventoryMovement.objects.create(
                warehouse_commodity=warehouse_commodity,
                movement_type='in',
                quantity=self.quantity,
                reference_number=f"ORDER-{self.id}",
                notes=f"Order confirmed - Origin: {self.origin}",
                created_by=self.user
            )
            
            # Update order status
            self.status = 'confirmed'
            self.availability_status = 'imported'
            self.inventory_movement = movement
            self.save(update_fields=['status', 'availability_status', 'inventory_movement', 'updated_at'])
            
            return True
        else:
            raise ValidationError("Failed to add quantity to warehouse")
    
    @transaction.atomic
    def reject_order(self, reason=""):
        """Reject the order"""
        if self.status != 'pending':
            raise ValidationError("Only pending orders can be rejected")
        
        self.status = 'rejected'
        self.save(update_fields=['status', 'updated_at'])
        
        # You can add logic here to notify the user about rejection
        return True
    
    @transaction.atomic
    def export_order(self):
        """Mark order as exported and remove from inventory"""
        if self.status != 'confirmed' or self.availability_status != 'imported':
            raise ValidationError("Only confirmed and imported orders can be exported")
        
        if self.inventory_movement:
            warehouse_commodity = self.inventory_movement.warehouse_commodity
            
            # Remove quantity from warehouse
            if warehouse_commodity.remove_quantity(self.quantity):
                # Create export movement record
                export_movement = InventoryMovement.objects.create(
                    warehouse_commodity=warehouse_commodity,
                    movement_type='out',
                    quantity=self.quantity,
                    reference_number=f"EXPORT-ORDER-{self.id}",
                    notes=f"Order exported - Destination: {self.origin}",
                    created_by=self.user
                )
                
                # Update order status
                self.availability_status = 'exported'
                self.save(update_fields=['availability_status', 'updated_at'])
                
                return True
            else:
                raise ValidationError("Failed to remove quantity from warehouse")
        else:
            raise ValidationError("No inventory movement record found for this order")










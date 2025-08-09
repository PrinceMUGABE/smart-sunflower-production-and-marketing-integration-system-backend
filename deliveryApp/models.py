# models.py - Add this to your existing models file

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from userApp.models import CustomUser
from driverApp.models import Driver
from vehicleApp.models import Vehicle
from orderApp.models import Order

class OrderDelivery(models.Model):
    """Model for managing order deliveries"""
    
    STATUS_CHOICES = [
        ('in_process', 'In Process'), 
        ('completed', 'Completed'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='deliveries')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='deliveries')
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='deliveries')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='in_process')
    
    # User who created the delivery (usually admin/staff)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_deliveries')
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Order Delivery"
        verbose_name_plural = "Order Deliveries"
        # Ensure one delivery per order
        unique_together = ['order']
    
    def __str__(self):
        return f"Delivery #{self.id} - Order #{self.order.id} - {self.get_status_display()}"
    
    def clean(self):
        """Validate delivery data"""
        errors = {}
        
        # Check if order exists and is confirmed
        if self.order:
            if self.order.status != 'confirmed':
                errors['order'] = "Only confirmed orders can be assigned for delivery"
            
            if self.order.availability_status != 'imported':
                errors['order'] = "Order must be imported before delivery can be assigned"
        
        # Check if driver exists and is approved
        if self.driver:
            if self.driver.status != 'approved':
                errors['driver'] = "Only approved drivers can be assigned to deliveries"
            
            if self.driver.availability_status != 'active':
                errors['driver'] = "Driver must be active to be assigned to deliveries"
        
        # Check if vehicle exists and is active
        if self.vehicle:
            if self.vehicle.status != 'active':
                errors['vehicle'] = "Only active vehicles can be assigned to deliveries"
        
        # Check if driver can handle the vehicle's driving category
        if self.driver and self.vehicle:
            if not self.driver.can_handle_driving_category(self.vehicle.driving_category):
                errors['driver'] = f"Driver cannot handle vehicles of category {self.vehicle.driving_category}"
        
        # Check if driver is already assigned to another in-process delivery
        if self.driver and self.status == 'in_process':
            existing_delivery = OrderDelivery.objects.filter(
                driver=self.driver,
                status='in_process'
            ).exclude(pk=self.pk if self.pk else None)
            
            if existing_delivery.exists():
                errors['driver'] = "Driver is already assigned to another in-process delivery"
        
        # Check if vehicle is already assigned to another in-process delivery
        if self.vehicle and self.status == 'in_process':
            existing_delivery = OrderDelivery.objects.filter(
                vehicle=self.vehicle,
                status='in_process'
            ).exclude(pk=self.pk if self.pk else None)
            
            if existing_delivery.exists():
                errors['vehicle'] = "Vehicle is already assigned to another in-process delivery"
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Override save to validate before saving"""
        self.full_clean()
        super().save(*args, **kwargs)
        
        
        
        

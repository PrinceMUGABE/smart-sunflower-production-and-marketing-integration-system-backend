from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from userApp.models import CustomUser

class SunflowerHarvest(models.Model):
    """Tracks sunflower harvests (no category/commodity tables needed)."""
    farmer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='harvests')
    harvest_date = models.DateField()
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Quantity in kilograms"
    )
    quality_grade = models.CharField(
        max_length=20,
        choices=[
            ('grade_a', 'Grade A (Premium)'),
            ('grade_b', 'Grade B (Standard)'),
            ('grade_c', 'Grade C (Basic)')
        ]
    )
    moisture_content = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Moisture content (%)"
    )
    oil_content = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Oil content (%)"
    )
    district = models.CharField(max_length=100, help_text="District of storage")
    sector = models.CharField(max_length=100, help_text="Sector of storage")
    cell = models.CharField(max_length=100, help_text="Cell of storage")
    village = models.CharField(max_length=100, help_text="Village of storage")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-harvest_date']

    def __str__(self):
        return f"{self.quantity} kg (Grade: {self.get_quality_grade_display()})"

class HarvestStock(models.Model):
    """Tracks current stock levels (replaces warehouse)."""
    harvest = models.OneToOneField(
        SunflowerHarvest,
        on_delete=models.CASCADE,
        related_name='stock'
    )
    current_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    last_updated = models.DateTimeField(auto_now=True)

    def clean(self):
        """Ensure stock doesn't exceed original harvest."""
        if self.current_quantity > self.harvest.quantity:
            raise ValidationError("Stock cannot exceed original harvest quantity")

    def __str__(self):
        return f"{self.current_quantity} kg remaining"

class HarvestMovement(models.Model):
    """Tracks stock movements (district/village replace warehouse)."""
    MOVEMENT_TYPES = [
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
        ('transfer', 'Transfer'),
        ('adjustment', 'Adjustment')
    ]
    stock = models.ForeignKey(
        HarvestStock,
        on_delete=models.CASCADE,
        related_name='movements'
    )
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    # Destination location (for transfers)
    to_district = models.CharField(max_length=100, blank=True, null=True)
    to_sector = models.CharField(max_length=100, blank=True, null=True)
    to_cell = models.CharField(max_length=100, blank=True, null=True)
    to_village = models.CharField(max_length=100, blank=True, null=True)
    # Source location (auto-filled from harvest)
    from_district = models.CharField(max_length=100, editable=False)
    from_sector = models.CharField(max_length=100, editable=False)
    from_cell = models.CharField(max_length=100, editable=False)
    from_village = models.CharField(max_length=100, editable=False)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True
    )
    movement_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-movement_date']

    def save(self, *args, **kwargs):
        """Auto-fill source location from harvest and update stock."""
        if not self.pk:  # New movement only
            self.from_district = self.stock.harvest.district
            self.from_sector = self.stock.harvest.sector
            self.from_cell = self.stock.harvest.cell
            self.from_village = self.stock.harvest.village

            # Update stock quantity
            if self.movement_type in ['out', 'transfer']:
                self.stock.current_quantity -= self.quantity
            elif self.movement_type == 'in':
                self.stock.current_quantity += self.quantity
            self.stock.save()
        super().save(*args, **kwargs)

    def clean(self):
        """Prevent negative stock."""
        if self.movement_type in ['out', 'transfer']:
            if self.quantity > self.stock.current_quantity:
                raise ValidationError(
                    f"Insufficient stock. Only {self.stock.current_quantity} kg available."
                )
        if self.movement_type == 'transfer' and not all([
            self.to_district, self.to_sector, self.to_cell, self.to_village
        ]):
            raise ValidationError("Destination location required for transfers")

    def __str__(self):
        return f"{self.get_movement_type_display()} of {self.quantity} kg"
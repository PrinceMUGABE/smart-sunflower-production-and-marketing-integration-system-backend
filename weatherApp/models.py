from django.db import models
from userApp.models import CustomUser

class CropRequirementPrediction(models.Model):
    # Location information
    district = models.CharField(max_length=100)
    sector = models.CharField(max_length=100)
    
    # Crop and season information
    crop = models.CharField(max_length=100)
    season = models.CharField(max_length=50)
    soil_type = models.CharField(max_length=100)
    altitude = models.CharField(max_length=250)
    
    # Base requirements
    nitrogen_kg_per_ha = models.FloatField()
    phosphorus_kg_per_ha = models.FloatField()
    potassium_kg_per_ha = models.FloatField()
    water_requirement_mm = models.FloatField()
    optimal_ph = models.FloatField(null=True, blank=True)
    
    # Planting information
    row_spacing_cm = models.IntegerField(null=True, blank=True)
    plant_spacing_cm = models.IntegerField(null=True, blank=True)
    planting_depth_cm = models.IntegerField(null=True, blank=True)
    
    # Yield information
    expected_yield_tons_per_ha = models.FloatField(null=True, blank=True)
    
    # Recommendations stored as JSON
    seasonal_recommendations = models.JSONField(default=list, blank=True)
    intercropping_recommendation = models.JSONField(default=list, null=True, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='crop_requirements')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('district', 'sector', 'crop', 'season')
        
    def __str__(self):
        return f"{self.crop} in {self.district}/{self.sector} ({self.season})"
    
    
    
    
    
 
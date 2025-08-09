   
from django.db import models
from userApp.models import CustomUser
from weatherApp.models import CropRequirementPrediction


class WeatherData(models.Model):
    # Location information
    district = models.CharField(max_length=100)
    sector = models.CharField(max_length=100)
    
    # Time period
    date_recorded = models.DateField(auto_now_add=True)
    season = models.CharField(max_length=50)
    
    # Monthly weather data (stored as JSON)
    monthly_data = models.JSONField(default=dict)
    
    # Seasonal summary data
    minor_dry_season_temp = models.FloatField(null=True, blank=True)
    minor_dry_season_rainfall = models.FloatField(null=True, blank=True)
    minor_dry_season_humidity = models.FloatField(null=True, blank=True)
    
    major_rainy_season_temp = models.FloatField(null=True, blank=True)
    major_rainy_season_rainfall = models.FloatField(null=True, blank=True)
    major_rainy_season_humidity = models.FloatField(null=True, blank=True)
    
    major_dry_season_temp = models.FloatField(null=True, blank=True)
    major_dry_season_rainfall = models.FloatField(null=True, blank=True)
    major_dry_season_humidity = models.FloatField(null=True, blank=True)
    
    minor_rainy_season_temp = models.FloatField(null=True, blank=True)
    minor_rainy_season_rainfall = models.FloatField(null=True, blank=True)
    minor_rainy_season_humidity = models.FloatField(null=True, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='weather_data')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Link to related crop prediction
    related_prediction = models.ForeignKey(CropRequirementPrediction, on_delete=models.SET_NULL, 
                                          null=True, blank=True, related_name='weather_records')
    
    class Meta:
        unique_together = ('district', 'sector', 'date_recorded')
        
    def __str__(self):
        return f"Weather data for {self.district}/{self.sector} on {self.date_recorded}"
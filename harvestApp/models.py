from django.db import models
from userApp.models import CustomUser

class Harvest(models.Model):
    # Location information
    district = models.CharField(max_length=100)
    sector = models.CharField(max_length=100)
    

    
    # Yield information
    harvest = models.FloatField(null=True, blank=True)
    
    # Recommendations stored as JSON
    season = models.CharField(max_length=30, default='')
    # Metadata
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sunflower_harvest')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('district', 'sector', 'season', 'harvest')
        
    def __str__(self):
        return f"{self.crop} in {self.district}/{self.sector} ({self.season})"
    
    
    
    
    
 
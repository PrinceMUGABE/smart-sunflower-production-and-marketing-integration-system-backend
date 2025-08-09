# serializers.py
from rest_framework import serializers
from .models import CropRequirementPrediction
from userApp.models import CustomUser



class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'phone_number', 'email', 'role', 'created_at']
        
        
        
class CropRequirementPredictionSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = CropRequirementPrediction
        fields = [
            'id', 'district', 'sector', 'crop', 'season', 'soil_type', 'altitude',
            'nitrogen_kg_per_ha', 'phosphorus_kg_per_ha', 'potassium_kg_per_ha',
            'water_requirement_mm', 'optimal_ph', 'row_spacing_cm', 'plant_spacing_cm',
            'planting_depth_cm', 'expected_yield_tons_per_ha', 'seasonal_recommendations',
            'intercropping_recommendation', 'created_by',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

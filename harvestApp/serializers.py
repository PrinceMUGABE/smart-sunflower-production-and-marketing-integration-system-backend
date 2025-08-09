# serializers.py
from rest_framework import serializers
from .models import Harvest
from userApp.models import CustomUser

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'phone_number', 'email', 'role', 'created_at']
        


class HarvestSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = Harvest
        fields = [
            'id',
            'district',
            'sector',
            'harvest',
            'season',
            'created_by',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
    
    def validate_harvest(self, value):
        """Validate that harvest value is positive"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Harvest value cannot be negative")
        return value
    
    def validate_season(self, value):
        """Validate season format"""
        if value and len(value.strip()) == 0:
            raise serializers.ValidationError("Season cannot be empty")
        return value.strip() if value else value


class HarvestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating harvest records"""
    
    class Meta:
        model = Harvest
        fields = [
            'district',
            'sector',
            'harvest',
            'season'
        ]
    
    def validate_harvest(self, value):
        """Validate that harvest value is positive"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Harvest value cannot be negative")
        return value
    
    def validate_season(self, value):
        """Validate season format"""
        if value and len(value.strip()) == 0:
            raise serializers.ValidationError("Season cannot be empty")
        return value.strip() if value else value


class HarvestUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating harvest records"""
    
    class Meta:
        model = Harvest
        fields = [
            'district',
            'sector',
            'harvest',
            'season'
        ]
    
    def validate_harvest(self, value):
        """Validate that harvest value is positive"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Harvest value cannot be negative")
        return value
    
    def validate_season(self, value):
        """Validate season format"""
        if value and len(value.strip()) == 0:
            raise serializers.ValidationError("Season cannot be empty")
        return value.strip() if value else value
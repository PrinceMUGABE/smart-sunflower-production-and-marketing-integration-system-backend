from rest_framework import serializers
from .models import SunflowerHarvest, HarvestStock, HarvestMovement
from userApp.models import CustomUser

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'phone_number', 'email', 'role', 'created_at']
        

class SunflowerHarvestSerializer(serializers.ModelSerializer):
    farmer = UserSerializer(read_only=True)
    remaining_quantity = serializers.SerializerMethodField()

    class Meta:
        model = SunflowerHarvest
        fields = [
            'id', 'farmer', 'harvest_date', 'quantity', 'remaining_quantity',
            'quality_grade', 'moisture_content', 'oil_content',
            'district', 'sector', 'cell', 'village', 'created_at'
        ]
        read_only_fields = ['farmer', 'created_at']

    def get_remaining_quantity(self, obj):
        return obj.stock.current_quantity if hasattr(obj, 'stock') else obj.quantity

class HarvestStockSerializer(serializers.ModelSerializer):
    location = serializers.SerializerMethodField()

    class Meta:
        model = HarvestStock
        fields = ['id', 'current_quantity', 'last_updated', 'location']
    
    def get_location(self, obj):
        return {
            'district': obj.harvest.district,
            'sector': obj.harvest.sector,
            'cell': obj.harvest.cell,
            'village': obj.harvest.village
        }

class HarvestMovementSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    source_location = serializers.SerializerMethodField()
    destination_location = serializers.SerializerMethodField()

    class Meta:
        model = HarvestMovement
        fields = [
            'id', 'movement_type', 'quantity', 'source_location',
            'destination_location', 'notes', 'created_by', 'movement_date'
        ]
        read_only_fields = ['created_by', 'movement_date']

    def get_source_location(self, obj):
        return {
            'district': obj.from_district,
            'sector': obj.from_sector,
            'cell': obj.from_cell,
            'village': obj.from_village
        }

    def get_destination_location(self, obj):
        if obj.movement_type == 'transfer':
            return {
                'district': obj.to_district,
                'sector': obj.to_sector,
                'cell': obj.to_cell,
                'village': obj.to_village
            }
        return None
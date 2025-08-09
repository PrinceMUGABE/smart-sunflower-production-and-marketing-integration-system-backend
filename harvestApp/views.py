# views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from .models import Harvest
from .serializers import HarvestSerializer, HarvestCreateSerializer, HarvestUpdateSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_harvest(request):
    """Create a new harvest record"""
    serializer = HarvestCreateSerializer(data=request.data)
    
    if serializer.is_valid():
        try:
            harvest = serializer.save(created_by=request.user)
            response_serializer = HarvestSerializer(harvest)
            return Response(
                {
                    'message': 'Harvest record created successfully',
                    'data': response_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        except IntegrityError:
            return Response(
                {
                    'error': 'A harvest record with this combination already exists'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    return Response(
        {
            'error': 'Invalid data provided',
            'details': serializer.errors
        },
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_harvests(request):
    """Get all harvest records"""
    harvests = Harvest.objects.all().order_by('-created_at')
    serializer = HarvestSerializer(harvests, many=True)
    
    return Response(
        {
            'message': 'All harvests retrieved successfully',
            'count': harvests.count(),
            'data': serializer.data
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_harvests(request):
    """Get harvests created by the logged-in user"""
    user_harvests = Harvest.objects.filter(created_by=request.user).order_by('-created_at')
    serializer = HarvestSerializer(user_harvests, many=True)
    
    return Response(
        {
            'message': 'User harvests retrieved successfully',
            'count': user_harvests.count(),
            'data': serializer.data
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_harvest_by_id(request, harvest_id):
    """Get a specific harvest record by ID"""
    harvest = get_object_or_404(Harvest, id=harvest_id)
    serializer = HarvestSerializer(harvest)
    
    return Response(
        {
            'message': 'Harvest retrieved successfully',
            'data': serializer.data
        },
        status=status.HTTP_200_OK
    )


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_harvest(request, harvest_id):
    """Update a harvest record"""
    harvest = get_object_or_404(Harvest, id=harvest_id)
    
    # Check if user is the owner or admin
    if harvest.created_by != request.user and request.user.role != 'admin':
        return Response(
            {
                'error': 'You do not have permission to update this harvest record'
            },
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Use partial update for PATCH method
    partial = request.method == 'PATCH'
    serializer = HarvestUpdateSerializer(harvest, data=request.data, partial=partial)
    
    if serializer.is_valid():
        try:
            updated_harvest = serializer.save()
            response_serializer = HarvestSerializer(updated_harvest)
            return Response(
                {
                    'message': 'Harvest record updated successfully',
                    'data': response_serializer.data
                },
                status=status.HTTP_200_OK
            )
        except IntegrityError:
            return Response(
                {
                    'error': 'A harvest record with this combination already exists'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    return Response(
        {
            'error': 'Invalid data provided',
            'details': serializer.errors
        },
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_harvest(request, harvest_id):
    """Delete a harvest record"""
    harvest = get_object_or_404(Harvest, id=harvest_id)
    
    # Check if user is the owner or admin
    if harvest.created_by != request.user and request.user.role != 'admin':
        return Response(
            {
                'error': 'You do not have permission to delete this harvest record'
            },
            status=status.HTTP_403_FORBIDDEN
        )
    
    harvest_data = HarvestSerializer(harvest).data
    harvest.delete()
    
    return Response(
        {
            'message': 'Harvest record deleted successfully',
            'deleted_data': harvest_data
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_harvests_by_location(request):
    """Get harvests filtered by district and/or sector"""
    district = request.GET.get('district')
    sector = request.GET.get('sector')
    
    harvests = Harvest.objects.all()
    
    if district:
        harvests = harvests.filter(district__icontains=district)
    
    if sector:
        harvests = harvests.filter(sector__icontains=sector)
    
    harvests = harvests.order_by('-created_at')
    serializer = HarvestSerializer(harvests, many=True)
    
    return Response(
        {
            'message': 'Harvests retrieved successfully',
            'filters': {
                'district': district,
                'sector': sector
            },
            'count': harvests.count(),
            'data': serializer.data
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_harvests_by_season(request, season):
    """Get harvests filtered by season"""
    harvests = Harvest.objects.filter(season__icontains=season).order_by('-created_at')
    serializer = HarvestSerializer(harvests, many=True)
    
    return Response(
        {
            'message': f'Harvests for {season} season retrieved successfully',
            'season': season,
            'count': harvests.count(),
            'data': serializer.data
        },
        status=status.HTTP_200_OK
    )
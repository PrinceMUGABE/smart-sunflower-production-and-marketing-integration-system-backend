# urls.py
from django.urls import path
from . import views

app_name = 'harvests'

urlpatterns = [
    # Main CRUD operations
    path('create/', views.create_harvest, name='create_harvest'),
    path('all/', views.get_all_harvests, name='get_all_harvests'),
    path('my-harvests/', views.get_user_harvests, name='get_user_harvests'),
    path('<int:harvest_id>/', views.get_harvest_by_id, name='get_harvest_by_id'),
    path('<int:harvest_id>/update/', views.update_harvest, name='update_harvest'),
    path('<int:harvest_id>/delete/', views.delete_harvest, name='delete_harvest'),
    
    # Additional filtering endpoints
    path('location/', views.get_harvests_by_location, name='get_harvests_by_location'),
    path('season/<str:season>/', views.get_harvests_by_season, name='get_harvests_by_season'),
]
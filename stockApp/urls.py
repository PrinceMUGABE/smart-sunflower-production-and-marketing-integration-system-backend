
from django.urls import path
from . import views


urlpatterns = [
    # Stock Management URLs
    path('create/', views.create_harvest_stock, name='create_harvest_stock'),
    path('stocks/', views.get_all_stocks, name='get_all_stocks'),
    path('<int:stock_id>/', views.get_stock_details, name='get_stock_details'),
    path('update/<int:stock_id>/', views.update_stock, name='update_stock'),
    path('delete/<int:stock_id>/', views.delete_stock, name='delete_stock'),
    
    # Farmer-specific URLs
    path('my-stocks/', views.get_farmer_stocks, name='get_farmer_stocks'),
    
    # Stock Movement URLs
    path('movements/create/', views.create_stock_movement, name='create_stock_movement'),
    path('<int:stock_id>/movements/', views.get_stock_movements_history, name='get_stock_movements_history'),
    
    # Availability and Status URLs
    path('availability/', views.get_harvest_availability_status, name='get_harvest_availability_status'),
    
    # Dashboard URLs
    path('dashboard/', views.get_dashboard_summary, name='get_dashboard_summary'),
]
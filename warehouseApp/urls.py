from django.urls import path
from . import views

urlpatterns = [
    # Warehouse URLs
    path('warehouses/', views.list_warehouses, name='list-warehouses'),
    path('create/', views.create_warehouse, name='create-warehouse'),
    path('<int:id>/', views.warehouse_detail, name='warehouse-detail'),
    path('user/', views.user_warehouses, name='user-warehouses'),
    
    # Category URLs
    path('categories/', views.categories, name='categories'),
    path('categories/<int:id>/', views.category_detail, name='category-detail'),
    
    # Commodity URLs
    path('commodities/', views.commodities, name='commodities'),
    path('commodities/<int:id>/', views.commodity_detail, name='commodity-detail'),
    
    # Warehouse-Commodity Management URLs
    path('warehouses/<int:warehouse_id>/commodities/', views.warehouse_commodities, name='warehouse-commodities'),
    path('warehouses/<int:warehouse_id>/commodities/add/', views.add_commodity_to_warehouse, name='add-commodity-to-warehouse'),
    path('warehouses/<int:warehouse_id>/commodities/<int:commodity_id>/', views.warehouse_commodity_detail, name='warehouse-commodity-detail'),
    
    # Inventory Management URLs
    path('inventory/update/', views.update_inventory, name='update-inventory'),
    path('warehouses/<int:warehouse_id>/movements/', views.warehouse_movements, name='inventory-movements'),
    
    # Reporting URLs
    path('reports/capacity/', views.warehouse_capacity_report, name='capacity-report'),
    
    
    # Warehouse-based category and commodity filtering
    path('warehouses/<int:warehouse_id>/categories/', views.warehouse_categories, name='warehouse-categories'),
    path('warehouses/<int:warehouse_id>/categories/available/', views.warehouse_available_categories, name='warehouse-available-categories'),
    
    # Category-based commodity filtering
    path('categories/<int:category_id>/commodities/', views.category_commodities, name='category-commodities'),
    
    # Warehouse and category combined filtering
    path('warehouses/<int:warehouse_id>/categories/<int:category_id>/commodities/', views.warehouse_category_commodities, name='warehouse-category-commodities'),
    path('warehouses/<int:warehouse_id>/categories/<int:category_id>/commodities/available/', views.warehouse_category_available_commodities, name='warehouse-category-available-commodities'),
    
    # Helper endpoint for dropdowns
    path('categories/with-commodities/', views.all_categories_with_commodities, name='categories-with-commodities'),
]
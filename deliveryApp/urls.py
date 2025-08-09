from django.urls import path
from . import views

urlpatterns = [
    # Delivery URLs
    path('create/', views.create_delivery, name='create_delivery'),
    path('deliveries/', views.get_all_deliveries, name='get_all_deliveries'),
    path('<int:delivery_id>/', views.get_delivery_by_id, name='get_delivery_by_id'),
    path('my-created/', views.get_deliveries_created_by_user, name='get_deliveries_created_by_user'),
    path('my-assigned/', views.get_deliveries_assigned_to_driver, name='get_deliveries_assigned_to_driver'),
    path('update/<int:delivery_id>/', views.update_delivery, name='update_delivery'),
    path('delete/<int:delivery_id>/', views.delete_delivery, name='delete_delivery'),
    
    path('customer/', views.get_deliveries_assigned_to_customer, name='get_deliveries_assigned_to_customer'),
]
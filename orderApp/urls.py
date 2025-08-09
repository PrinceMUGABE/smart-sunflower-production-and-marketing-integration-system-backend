from django.urls import path
from . import views

urlpatterns = [
    # Order CRUD operations
    path('create/', views.create_order, name='create_order'),
    path('orders/', views.get_all_orders, name='get_all_orders'),
    path('user/', views.get_user_orders, name='get_user_orders'),
    path('<int:order_id>/', views.get_order_by_id, name='get_order_by_id'),
    path('<int:order_id>/update/', views.update_order, name='update_order'),
    path('<int:order_id>/delete/', views.delete_order, name='delete_order'),
    
    # Order actions (admin only)
    path('<int:order_id>/confirm/', views.confirm_order, name='confirm_order'),
    path('<int:order_id>/reject/', views.reject_order, name='reject_order'),
    
    path('<int:order_id>/export/', views.export_order, name='export_order'),
]


from django.urls import path
from . import views

urlpatterns = [
    # Farmer endpoints
    path('create/', views.create_sell_post, name='create_sell_post'),
    path('my-sells/', views.get_user_sells, name='get_user_sells'),
    path('update/<int:sell_id>/', views.update_sell, name='update_sell'),
    path('delete/<int:sell_id>/', views.delete_sell, name='delete_sell'),
    path('complete/<int:sell_id>/', views.complete_sell, name='complete_sell'),
    
    # Buyer endpoints
    path('available/', views.get_available_sells, name='get_available_sells'),
    path('purchase/<int:sell_id>/', views.purchase_sell, name='purchase_sell'),
    path('my-purchases/', views.get_user_purchases, name='get_user_purchases'),
    
    # General endpoints
    path('<int:sell_id>/', views.get_sell_by_id, name='get_sell_by_id'),
    
    # Payment endpoints
    path('payments/create/', views.create_payment, name='create_payment'),
    path('payments/update-status/<int:sell_id>/', views.update_payment_status, name='update_payment_status'),
    
    # Admin endpoints
    path('all/', views.get_all_sells, name='get_all_sells'),
    path('farmer/<int:farmer_id>/', views.get_farmer_sells, name='get_farmer_sells'),
    path('buyer/<int:buyer_id>/', views.get_buyer_purchases, name='get_buyer_purchases'),
]
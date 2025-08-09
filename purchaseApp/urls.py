# purchaseApp/urls.py
from django.urls import path
from . import views


urlpatterns = [
    # Purchase management
    path('purchase/', views.purchase_sell, name='purchase_sell'),
    path('purchases/', views.get_all_purchases, name='get_all_purchases'),
    path('my-purchases/', views.get_user_purchases, name='get_user_purchases'),
    path('purchases/<int:purchase_id>/', views.update_purchase, name='update_purchase'),
    path('purchases/<int:purchase_id>/status/', views.update_purchase_status, name='update_purchase_status'),
    path('purchases/<int:purchase_id>/delete/', views.delete_purchase, name='delete_purchase'),
    
    # Farmer's sell purchases
    path('farmer-purchases/', views.get_farmer_sell_purchases, name='get_farmer_sell_purchases'),
    
    # Payment management
    path('payments/make/', views.make_payment, name='make_payment'),
    path('purchases/<int:purchase_id>/payments/', views.get_purchase_payments, name='get_purchase_payments'),
    path('payments/<int:payment_id>/confirm/', views.confirm_payment, name='confirm_payment'),
]
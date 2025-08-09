from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.make_weather_adjusted_crop_prediction, name='predict_weather'),
    path('predictions/', views.get_all_predictions, name='all-predictions'),
    path('<int:pk>/', views.get_prediction_by_id, name='get-prediction'),
    path('update/<int:pk>/', views.update_prediction, name='update-prediction'),
    path('delete/<int:pk>/', views.delete_prediction, name='delete-prediction'),
    path('user/', views.get_user_predictions, name='user-predictions'),
]

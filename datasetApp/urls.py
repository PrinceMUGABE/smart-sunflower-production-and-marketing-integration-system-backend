# urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Dataset management URLs
    path('datasets/', views.list_datasets, name='list_datasets'),
    path('datasets/<str:dataset_name>/preview/', views.dataset_preview, name='dataset_preview'),
    path('datasets/<str:dataset_name>/update/', views.update_dataset, name='update_dataset'),
]
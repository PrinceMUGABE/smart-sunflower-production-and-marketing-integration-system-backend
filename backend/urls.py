
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('userApp.urls')),
    path('weather/', include('weatherApp.urls')),
    path('dataset/', include('datasetApp.urls')),
    path('feedback/', include('feedbackApp.urls')),
    path('harvest/', include('harvestApp.urls')),
    path('stock/', include('stockApp.urls')),
    path('sales/', include('sellsApp.urls')),
    path('purchase/', include('purchaseApp.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

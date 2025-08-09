# purchaseApp/apps.py
from django.apps import AppConfig


class PurchaseappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'purchaseApp'
    verbose_name = 'Purchase Management'
    
    def ready(self):
        # Import signals if you have any
        import purchaseApp.signals
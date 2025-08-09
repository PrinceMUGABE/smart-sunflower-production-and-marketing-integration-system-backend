from django.contrib import admin
from .models import Sell, SellPayment
from userApp.models import CustomUser


@admin.register(Sell)
class SellAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'farmer', 'buyer', 'quantity_sold', 'unit_price', 'total_amount',
        'sell_status', 'payment_status', 'sell_date', 'purchased_date', 'created_at'
    ]
    list_filter = [
        'sell_status', 'payment_status', 'sell_date', 'purchased_date', 'created_at',
        'harvest_stock__harvest__quality_grade', 'harvest_stock__harvest__district'
    ]
    search_fields = [
        'farmer__phone_number', 'buyer__phone_number', 'buyer_name', 'buyer_phone',
        'harvest_stock__harvest__district', 'harvest_stock__harvest__sector'
    ]
    readonly_fields = [
        'total_amount', 'payment_status', 'amount_paid', 'purchased_date',
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('farmer', 'harvest_stock', 'sell_date')
        }),
        ('Sale Details', {
            'fields': ('quantity_sold', 'unit_price', 'total_amount', 'sell_status')
        }),
        ('Buyer Information', {
            'fields': ('buyer', 'buyer_name', 'buyer_phone', 'buyer_email', 'buyer_address')
        }),
        ('Payment Information', {
            'fields': ('payment_status', 'amount_paid')
        }),
        ('Delivery Information', {
            'fields': ('delivery_date', 'delivery_address', 'delivery_notes')
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('purchased_date', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'farmer', 'buyer', 'harvest_stock__harvest'
        )
    
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)
        
        # Make buyer fields readonly after purchase
        if obj and obj.sell_status in ['purchased', 'completed']:
            readonly_fields.extend(['buyer', 'farmer', 'harvest_stock', 'quantity_sold', 'unit_price'])
        
        return readonly_fields
    
    def save_model(self, request, obj, form, change):
        """Custom save to handle business logic."""
        # Auto-fill buyer info when buyer is assigned
        if obj.buyer and not obj.buyer_name:
            obj.buyer_name = obj.buyer.phone_number
            obj.buyer_phone = obj.buyer.phone_number
            obj.buyer_email = obj.buyer.email or ""
        
        super().save_model(request, obj, form, change)


@admin.register(SellPayment)
class SellPaymentAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'sell', 'amount', 'payment_date', 'payment_method',
        'reference_number', 'paid_by', 'created_at'
    ]
    list_filter = ['payment_method', 'payment_date', 'created_at']
    search_fields = [
        'sell__farmer__phone_number', 'sell__buyer__phone_number',
        'reference_number', 'paid_by__phone_number'
    ]
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('sell', 'amount', 'payment_date', 'payment_method', 'paid_by')
        }),
        ('Reference & Notes', {
            'fields': ('reference_number', 'notes')
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'sell__farmer', 'sell__buyer', 'paid_by'
        )
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Customize foreign key fields."""
        if db_field.name == "paid_by":
            # Only show users who can make payments (buyers and the sell's farmer)
            kwargs["queryset"] = CustomUser.objects.filter(
                role__in=['buyer', 'farmer']
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
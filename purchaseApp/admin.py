# purchaseApp/admin.py
from datetime import timezone
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Purchase, PurchasePayment


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'buyer_info', 'sell_info', 'quantity_purchased',
        'total_amount', 'amount_paid', 'remaining_balance_display',
        'purchase_status', 'payment_progress_display', 'purchased_date'
    ]
    list_filter = [
        'purchase_status', 'purchased_date', 'expected_delivery_date',
        'sell__farmer', 'buyer'
    ]
    search_fields = [
        'buyer__phone_number', 'sell__farmer__phone_number',
        'delivery_address', 'notes'
    ]
    readonly_fields = [
        'total_amount', 'quantity_purchased', 'unit_price',
        'purchased_date', 'updated_at', 'completed_payment_date',
        'payment_progress_display', 'remaining_balance_display'
    ]
    fieldsets = (
        ('Purchase Information', {
            'fields': (
                'buyer', 'sell', 'quantity_purchased', 'unit_price',
                'total_amount', 'amount_paid'
            )
        }),
        ('Delivery Information', {
            'fields': (
                'delivery_address', 'delivery_notes', 'expected_delivery_date',
                'actual_delivery_date'
            )
        }),
        ('Status & Progress', {
            'fields': (
                'purchase_status', 'payment_progress_display',
                'remaining_balance_display'
            )
        }),
        ('Timestamps', {
            'fields': (
                'purchased_date', 'updated_at', 'completed_payment_date'
            ),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        })
    )
    
    def buyer_info(self, obj):
        return f"{obj.buyer.phone_number}"
    buyer_info.short_description = "Buyer"
    
    def sell_info(self, obj):
        farmer_phone = obj.sell.farmer.phone_number
        return f"Sell #{obj.sell.id} by {farmer_phone}"
    sell_info.short_description = "Sell"
    
    def remaining_balance_display(self, obj):
        balance = obj.remaining_balance
        if balance > 0:
            return format_html(
                '<span style="color: red; font-weight: bold;">${}</span>',
                balance
            )
        return format_html('<span style="color: green;">Fully Paid</span>')
    remaining_balance_display.short_description = "Remaining Balance"
    
    def payment_progress_display(self, obj):
        progress = obj.payment_progress
        color = 'red' if progress < 50 else 'orange' if progress < 100 else 'green'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color, progress
        )
    payment_progress_display.short_description = "Payment Progress"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'buyer', 'sell', 'sell__farmer'
        )


@admin.register(PurchasePayment)
class PurchasePaymentAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'purchase_info', 'amount', 'payment_method',
        'status_display', 'paypack_ref', 'transaction_date'
    ]
    list_filter = [
        'status', 'payment_method', 'transaction_date', 'completed_date'
    ]
    search_fields = [
        'purchase__buyer__phone_number', 'paypack_ref',
        'reference_number', 'phone_number'
    ]
    readonly_fields = [
        'transaction_date', 'completed_date', 'paypack_ref',
        'paypack_status'
    ]
    fieldsets = (
        ('Payment Information', {
            'fields': (
                'purchase', 'amount', 'payment_method', 'phone_number'
            )
        }),
        ('PayPack Details', {
            'fields': (
                'paypack_ref', 'paypack_status'
            )
        }),
        ('Status & Tracking', {
            'fields': (
                'status', 'reference_number', 'transaction_date',
                'completed_date'
            )
        }),
        ('Additional Information', {
            'fields': ('notes', 'failure_reason'),
            'classes': ('collapse',)
        })
    )
    
    def purchase_info(self, obj):
        buyer_phone = obj.purchase.buyer.phone_number
        return f"Purchase #{obj.purchase.id} by {buyer_phone}"
    purchase_info.short_description = "Purchase"
    
    def status_display(self, obj):
        status_colors = {
            'pending': 'orange',
            'completed': 'green',
            'failed': 'red',
            'cancelled': 'gray'
        }
        color = status_colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = "Status"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'purchase', 'purchase__buyer'
        )


# Custom admin actions
def mark_payments_as_completed(modeladmin, request, queryset):
    """Mark selected payments as completed."""
    updated = 0
    for payment in queryset.filter(status='pending'):
        payment.status = 'completed'
        payment.completed_date = timezone.now()
        payment.save()
        updated += 1
    
    modeladmin.message_user(
        request,
        f"Successfully marked {updated} payments as completed."
    )
mark_payments_as_completed.short_description = "Mark selected payments as completed"

def mark_purchases_as_delivered(modeladmin, request, queryset):
    """Mark selected purchases as delivered."""
    updated = 0
    for purchase in queryset.filter(purchase_status='fully_paid'):
        purchase.purchase_status = 'delivered'
        purchase.actual_delivery_date = timezone.now().date()
        purchase.save()
        updated += 1
    
    modeladmin.message_user(
        request,
        f"Successfully marked {updated} purchases as delivered."
    )
mark_purchases_as_delivered.short_description = "Mark selected purchases as delivered"

# Add actions to admin classes
PurchasePaymentAdmin.actions = [mark_payments_as_completed]
PurchaseAdmin.actions = [mark_purchases_as_delivered]
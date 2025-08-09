# purchaseApp/signals.py
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import Purchase, PurchasePayment
from django.db import models


@receiver(post_save, sender=PurchasePayment)
def update_purchase_on_payment(sender, instance, created, **kwargs):
    """
    Update purchase status and amounts when a payment is saved.
    """
    if instance.status == 'completed':
        purchase = instance.purchase
        
        # Recalculate total completed payments
        total_paid = purchase.payments.filter(status='completed').aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        
        # Update purchase amount_paid
        if purchase.amount_paid != total_paid:
            purchase.amount_paid = total_paid
            purchase.save()


@receiver(pre_delete, sender=Purchase)
def reset_sell_on_purchase_delete(sender, instance, **kwargs):
    """
    Reset sell status when a purchase is deleted.
    """
    sell = instance.sell
    if sell:
        sell.sell_status = 'posted'
        sell.buyer = None
        sell.amount_paid = 0
        sell.payment_status = 'unpaid'
        sell.delivery_address = ''
        sell.purchased_date = None
        sell.payment_completed_date = None
        sell.delivery_date = None
        sell.save()


@receiver(post_save, sender=Purchase)
def update_sell_on_purchase_save(sender, instance, created, **kwargs):
    """
    Update sell status when purchase is saved.
    """
    if created:
        # When a purchase is created, update the sell
        sell = instance.sell
        sell.sell_status = 'purchased'
        sell.buyer = instance.buyer
        sell.delivery_address = instance.delivery_address
        sell.purchased_date = instance.purchased_date
        sell.save()
    else:
        # When purchase is updated, sync with sell
        sell = instance.sell
        
        # Update sell payment information
        sell.amount_paid = instance.amount_paid
        if instance.amount_paid >= instance.total_amount:
            sell.payment_status = 'paid'
            sell.payment_completed_date = instance.completed_payment_date
            sell.delivery_date = instance.expected_delivery_date
        elif instance.amount_paid > 0:
            sell.payment_status = 'partial'
        else:
            sell.payment_status = 'unpaid'
        
        # Update sell status based on purchase status
        if instance.purchase_status == 'delivered':
            sell.sell_status = 'completed'
        elif instance.purchase_status == 'cancelled':
            sell.sell_status = 'cancelled'
        
        sell.save()
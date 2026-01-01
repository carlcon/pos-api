"""
Utility functions for notifications.
"""
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def send_store_transfer_email(user, old_store, new_store):
    """Send email notification when store admin is transferred."""
    if not user.email:
        return
    
    subject = 'Store Assignment Changed'
    
    # Simple text email (can be replaced with HTML template)
    message = f"""
Hello {user.first_name or user.username},

Your store assignment has been changed.

Previous Store: {old_store.name if old_store else 'None'}
New Store: {new_store.name}

If you have any questions, please contact your administrator.

Best regards,
POS Inventory Team
"""
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info(f"Store transfer email sent to {user.email}")
    except Exception as e:
        logger.error(f"Failed to send store transfer email to {user.email}: {e}")


def send_stock_alert_email(user, product, alert_type):
    """Send email notification for stock alerts."""
    if not user.email:
        return
    
    if alert_type == 'low':
        subject = f'Low Stock Alert: {product.name}'
        message = f"""
Hello {user.first_name or user.username},

The following product is running low on stock:

Product: {product.name}
SKU: {product.sku}
Current Quantity: {product.quantity}
Low Stock Threshold: {product.low_stock_threshold}

Please reorder soon to avoid stockouts.

Best regards,
POS Inventory Team
"""
    else:  # out_of_stock
        subject = f'Out of Stock Alert: {product.name}'
        message = f"""
Hello {user.first_name or user.username},

The following product is OUT OF STOCK:

Product: {product.name}
SKU: {product.sku}
Current Quantity: 0

Please reorder immediately.

Best regards,
POS Inventory Team
"""
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info(f"Stock alert email sent to {user.email}")
    except Exception as e:
        logger.error(f"Failed to send stock alert email to {user.email}: {e}")


def send_sms_notification(phone_number, message):
    """
    Send SMS notification using free SMS service.
    For MVP, we'll use TextBelt free tier (1 SMS/day) or email-to-SMS gateway.
    """
    if not phone_number:
        return False
    
    # Try TextBelt free tier first
    try:
        import requests
        
        response = requests.post(
            'https://textbelt.com/text',
            data={
                'phone': phone_number,
                'message': message,
                'key': 'textbelt',  # Free tier key
            },
            timeout=10
        )
        
        result = response.json()
        if result.get('success'):
            logger.info(f"SMS sent to {phone_number}")
            return True
        else:
            logger.warning(f"TextBelt SMS failed: {result.get('error')}")
    except Exception as e:
        logger.error(f"Failed to send SMS to {phone_number}: {e}")
    
    return False


def create_notification(user, notification_type, title, message, data=None):
    """Helper function to create a notification."""
    from notifications.models import Notification
    
    return Notification.objects.create(
        user=user,
        type=notification_type,
        title=title,
        message=message,
        data=data
    )


def create_stock_alert_notifications(product, alert_type='low'):
    """
    Create notifications for all store admins when stock is low or out.
    """
    from users.models import User
    from notifications.models import Notification
    
    notification_type = (
        Notification.Type.LOW_STOCK_ALERT 
        if alert_type == 'low' 
        else Notification.Type.OUT_OF_STOCK_ALERT
    )
    
    title = f'{"Low" if alert_type == "low" else "Out of"} Stock: {product.name}'
    message = f'{product.name} (SKU: {product.sku}) is {"running low" if alert_type == "low" else "out of stock"}. Current quantity: {product.quantity}'
    
    # Get all store admins for this product's store
    store_admins = User.objects.filter(
        assigned_store=product.store,
        role=User.Role.STORE_ADMIN,
        is_active=True
    )
    
    for admin in store_admins:
        create_notification(
            user=admin,
            notification_type=notification_type,
            title=title,
            message=message,
            data={
                'product_id': product.id,
                'product_name': product.name,
                'product_sku': product.sku,
                'quantity': product.quantity,
                'store_id': product.store_id if product.store else None,
            }
        )
        
        # Send email
        send_stock_alert_email(admin, product, alert_type)
        
        # Send SMS for out of stock (critical)
        if alert_type == 'out' and admin.sms_phone:
            send_sms_notification(
                admin.sms_phone,
                f'OUT OF STOCK: {product.name}. Quantity: 0. Please reorder immediately.'
            )

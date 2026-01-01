"""
Signals for notifications app.
Listens for events and creates notifications.
"""
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver


@receiver(pre_save, sender='users.User')
def track_user_store_changes(sender, instance, **kwargs):
    """Track store assignment changes for audit logging."""
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            instance._old_assigned_store = old_instance.assigned_store
            instance._old_role = old_instance.role
        except sender.DoesNotExist:
            instance._old_assigned_store = None
            instance._old_role = None
    else:
        instance._old_assigned_store = None
        instance._old_role = None


@receiver(post_save, sender='users.User')
def create_store_audit_log(sender, instance, created, **kwargs):
    """Create audit log when store assignment changes."""
    from users.models import StoreAdminAuditLog
    
    old_store = getattr(instance, '_old_assigned_store', None)
    old_role = getattr(instance, '_old_role', None)
    new_store = instance.assigned_store
    new_role = instance.role
    
    # Only log if store or role changed
    store_changed = old_store != new_store
    role_changed = old_role != new_role
    
    if not store_changed and not role_changed:
        return
    
    # Determine action
    if created or (old_store is None and new_store is not None):
        action = StoreAdminAuditLog.Action.ASSIGNED
    elif old_store is not None and new_store is None:
        action = StoreAdminAuditLog.Action.REMOVED
    elif store_changed:
        action = StoreAdminAuditLog.Action.MOVED
    elif role_changed:
        action = StoreAdminAuditLog.Action.ROLE_CHANGED
    else:
        return
    
    # Create audit log
    StoreAdminAuditLog.objects.create(
        user=instance,
        action=action,
        old_store=old_store,
        new_store=new_store,
        old_role=old_role,
        new_role=new_role,
        changed_by=None,  # Will be set by the view if available
    )
    
    # Create notification for the user if they were transferred
    if action == StoreAdminAuditLog.Action.MOVED and new_store:
        from notifications.models import Notification
        
        Notification.objects.create(
            user=instance,
            type=Notification.Type.STORE_ADMIN_TRANSFER,
            title='Store Assignment Changed',
            message=f'You have been transferred to {new_store.name}.',
            data={
                'old_store_id': old_store.id if old_store else None,
                'old_store_name': old_store.name if old_store else None,
                'new_store_id': new_store.id,
                'new_store_name': new_store.name,
            }
        )
        
        # Send email notification
        try:
            from notifications.utils import send_store_transfer_email
            send_store_transfer_email(instance, old_store, new_store)
        except Exception:
            pass  # Don't fail if email sending fails


@receiver(pre_save, sender='stores.Store')
def track_store_active_changes(sender, instance, **kwargs):
    """Track store is_active changes."""
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            instance._old_is_active = old_instance.is_active
        except sender.DoesNotExist:
            instance._old_is_active = None
    else:
        instance._old_is_active = None


@receiver(post_save, sender='stores.Store')
def handle_store_deactivation(sender, instance, created, **kwargs):
    """Handle store activation/deactivation."""
    from users.models import User
    from notifications.models import Notification
    
    if created:
        return
    
    old_is_active = getattr(instance, '_old_is_active', None)
    
    # Store was deactivated
    if old_is_active and not instance.is_active:
        # Disable all store users
        affected_users = User.objects.filter(
            assigned_store=instance,
            is_active=True
        )
        
        for user in affected_users:
            user.is_active = False
            user.save(update_fields=['is_active'])
            
            # Create notification
            Notification.objects.create(
                user=user,
                type=Notification.Type.STORE_DEACTIVATED,
                title='Store Deactivated',
                message=f'Your store "{instance.name}" has been deactivated. Your account has been disabled.',
                data={'store_id': instance.id, 'store_name': instance.name}
            )
    
    # Store was reactivated
    elif not old_is_active and instance.is_active:
        # Re-enable all store users
        affected_users = User.objects.filter(
            assigned_store=instance,
            is_active=False
        )
        
        for user in affected_users:
            user.is_active = True
            user.save(update_fields=['is_active'])
            
            # Create notification
            Notification.objects.create(
                user=user,
                type=Notification.Type.STORE_ACTIVATED,
                title='Store Reactivated',
                message=f'Your store "{instance.name}" has been reactivated. Your account has been re-enabled.',
                data={'store_id': instance.id, 'store_name': instance.name}
            )

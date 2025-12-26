from django.db.models.signals import post_save
from django.dispatch import receiver
from users.models import Partner
from .models import Store


@receiver(post_save, sender=Partner)
def create_default_store(sender, instance: Partner, created: bool, **kwargs):
    """Create a default store for a partner if none exist."""
    if not created:
        return

    if Store.objects.filter(partner=instance).exists():
        return

    Store.objects.create(
        partner=instance,
        name=f"{instance.name} - Default",
        code=f"{instance.code}-DEFAULT",
        is_default=True,
        is_active=True,
    )

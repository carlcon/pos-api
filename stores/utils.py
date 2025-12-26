from typing import Optional
from users.models import Partner
from .models import Store


def get_default_store(partner: Optional[Partner]) -> Optional[Store]:
    if partner is None:
        return None
    return Store.objects.filter(partner=partner, is_default=True).first()

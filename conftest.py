import pytest
from django.contrib.auth import get_user_model
from users.models import User

User = get_user_model()


@pytest.fixture
def admin_user(db):
    """Create an admin user"""
    return User.objects.create_user(
        username='admin',
        email='admin@test.com',
        password='testpass123',
        role=User.Role.ADMIN
    )


@pytest.fixture
def inventory_staff_user(db):
    """Create an inventory staff user"""
    return User.objects.create_user(
        username='inventory_staff',
        email='inventory@test.com',
        password='testpass123',
        role=User.Role.INVENTORY_STAFF
    )


@pytest.fixture
def cashier_user(db):
    """Create a cashier user"""
    return User.objects.create_user(
        username='cashier',
        email='cashier@test.com',
        password='testpass123',
        role=User.Role.CASHIER
    )


@pytest.fixture
def viewer_user(db):
    """Create a viewer user"""
    return User.objects.create_user(
        username='viewer',
        email='viewer@test.com',
        password='testpass123',
        role=User.Role.VIEWER
    )

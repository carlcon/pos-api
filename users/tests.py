import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    """Test User model"""
    
    def test_create_user(self):
        """Test creating a new user"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role=User.Role.CASHIER
        )
        
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.role == User.Role.CASHIER
        assert user.check_password('testpass123')
    
    def test_user_role_properties(self):
        """Test user role properties"""
        admin = User.objects.create_user(
            username='admin',
            password='pass',
            role=User.Role.ADMIN
        )
        
        assert admin.is_admin is True
        assert admin.is_inventory_staff is False
        assert admin.is_cashier is False
        assert admin.is_viewer is False
    
    def test_user_str_representation(self):
        """Test user string representation"""
        user = User.objects.create_user(
            username='john',
            password='pass',
            role=User.Role.INVENTORY_STAFF
        )
        
        assert str(user) == "john (Inventory Staff)"


@pytest.mark.django_db
class TestUserPermissions:
    """Test user permissions"""
    
    def test_admin_permissions(self, admin_user):
        """Test admin has correct permissions"""
        assert admin_user.is_admin is True
    
    def test_inventory_staff_permissions(self, inventory_staff_user):
        """Test inventory staff has correct permissions"""
        assert inventory_staff_user.is_inventory_staff is True
    
    def test_cashier_permissions(self, cashier_user):
        """Test cashier has correct permissions"""
        assert cashier_user.is_cashier is True
    
    def test_viewer_permissions(self, viewer_user):
        """Test viewer has correct permissions"""
        assert viewer_user.is_viewer is True

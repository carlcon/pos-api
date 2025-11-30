"""
Comprehensive tests for Users Module.
Tests for: User model, permissions, serializers, views, authentication, partners, and impersonation.
"""
import pytest
from decimal import Decimal
from rest_framework import status
from users.models import User, Partner
from users.permissions import (
    IsAdmin, IsInventoryStaffOrAdmin, IsCashierOrAbove,
    CanDeleteProducts, CanAdjustStock
)
from users.serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer, ChangePasswordSerializer
)


# ============== User Model Tests ==============

@pytest.mark.django_db
class TestUserModel:
    """Test cases for User model"""
    
    def test_create_user(self, partner):
        """Test creating a new user"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role=User.Role.CASHIER,
            partner=partner
        )
        
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.role == User.Role.CASHIER
        assert user.check_password('testpass123')
    
    def test_create_admin_user(self, partner):
        """Test creating an admin user"""
        admin = User.objects.create_user(
            username='admin_test',
            email='admin@example.com',
            password='adminpass123',
            role=User.Role.ADMIN,
            partner=partner
        )
        
        assert admin.role == User.Role.ADMIN
        assert admin.is_admin
    
    def test_create_inventory_staff(self, partner):
        """Test creating inventory staff user"""
        staff = User.objects.create_user(
            username='inventory_staff_test',
            email='staff@example.com',
            password='staffpass123',
            role=User.Role.INVENTORY_STAFF,
            partner=partner
        )
        
        assert staff.role == User.Role.INVENTORY_STAFF
        assert staff.is_inventory_staff
    
    def test_create_cashier(self, partner):
        """Test creating cashier user"""
        cashier = User.objects.create_user(
            username='cashier_test',
            email='cashier@example.com',
            password='cashierpass123',
            role=User.Role.CASHIER,
            partner=partner
        )
        
        assert cashier.role == User.Role.CASHIER
        assert cashier.is_cashier
    
    def test_create_viewer(self, partner):
        """Test creating viewer user"""
        viewer = User.objects.create_user(
            username='viewer_test',
            email='viewer@example.com',
            password='viewerpass123',
            role=User.Role.VIEWER,
            partner=partner
        )
        
        assert viewer.role == User.Role.VIEWER
        assert viewer.is_viewer
    
    def test_user_role_properties_admin(self, partner):
        """Test admin user role properties"""
        admin = User.objects.create_user(
            username='admin_role_test',
            password='pass',
            role=User.Role.ADMIN,
            partner=partner
        )
        
        assert admin.is_admin
        assert not admin.is_inventory_staff
        assert not admin.is_cashier
        assert not admin.is_viewer
    
    def test_user_role_properties_inventory_staff(self, partner):
        """Test inventory staff user role properties"""
        staff = User.objects.create_user(
            username='staff_role_test',
            password='pass',
            role=User.Role.INVENTORY_STAFF,
            partner=partner
        )
        
        assert not staff.is_admin
        assert staff.is_inventory_staff
        assert not staff.is_cashier
        assert not staff.is_viewer
    
    def test_user_role_properties_cashier(self, partner):
        """Test cashier user role properties"""
        cashier = User.objects.create_user(
            username='cashier_role_test',
            password='pass',
            role=User.Role.CASHIER,
            partner=partner
        )
        
        assert not cashier.is_admin
        assert not cashier.is_inventory_staff
        assert cashier.is_cashier
        assert not cashier.is_viewer
    
    def test_user_role_properties_viewer(self, partner):
        """Test viewer user role properties"""
        viewer = User.objects.create_user(
            username='viewer_role_test',
            password='pass',
            role=User.Role.VIEWER,
            partner=partner
        )
        
        assert not viewer.is_admin
        assert not viewer.is_inventory_staff
        assert not viewer.is_cashier
        assert viewer.is_viewer
    
    def test_user_str_representation(self, partner):
        """Test user string representation"""
        user = User.objects.create_user(
            username='john',
            password='pass',
            role=User.Role.INVENTORY_STAFF,
            partner=partner
        )
        
        assert 'john' in str(user)
    
    def test_user_with_employee_id(self, partner):
        """Test user with employee ID"""
        user = User.objects.create_user(
            username='employee_test',
            password='pass',
            role=User.Role.CASHIER,
            employee_id='EMP-001',
            partner=partner
        )
        
        assert user.employee_id == 'EMP-001'
    
    def test_user_is_active_employee(self, partner):
        """Test user is_active_employee field"""
        active_user = User.objects.create_user(
            username='active_test',
            password='pass',
            role=User.Role.CASHIER,
            is_active_employee=True,
            partner=partner
        )
        inactive_user = User.objects.create_user(
            username='inactive_test',
            password='pass',
            role=User.Role.CASHIER,
            is_active_employee=False,
            partner=partner
        )
        
        assert active_user.is_active_employee
        assert not inactive_user.is_active_employee


# ============== User Serializer Tests ==============

@pytest.mark.django_db
class TestUserSerializer:
    """Test cases for User serializers"""
    
    def test_user_serializer_fields(self, admin_user):
        """Test UserSerializer contains expected fields"""
        serializer = UserSerializer(admin_user)
        expected_fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'is_active_employee', 'is_active'
        ]
        for field in expected_fields:
            assert field in serializer.data
    
    def test_user_serializer_data(self, admin_user):
        """Test UserSerializer data is correct"""
        serializer = UserSerializer(admin_user)
        assert serializer.data['username'] == admin_user.username


@pytest.mark.django_db
class TestUserCreateSerializer:
    """Test cases for UserCreateSerializer"""
    
    def test_valid_user_creation(self, partner):
        """Test valid user creation"""
        data = {
            'username': 'newuser_create',
            'email': 'newuser@example.com',
            'password': 'securepass123',
            'first_name': 'New',
            'last_name': 'User',
            'role': 'CASHIER'
        }
        serializer = UserCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
    
    def test_short_password_fails(self):
        """Test password minimum length validation"""
        data = {
            'username': 'shortpass',
            'email': 'short@example.com',
            'password': 'short',
            'role': 'CASHIER'
        }
        serializer = UserCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'password' in serializer.errors


@pytest.mark.django_db
class TestUserUpdateSerializer:
    """Test cases for UserUpdateSerializer"""
    
    def test_update_user_email(self, admin_user):
        """Test updating user email"""
        data = {'email': 'newemail@example.com'}
        serializer = UserUpdateSerializer(admin_user, data=data, partial=True)
        assert serializer.is_valid()
        user = serializer.save()
        
        assert user.email == 'newemail@example.com'
    
    def test_update_user_role(self, cashier_user):
        """Test updating user role"""
        data = {'role': 'INVENTORY_STAFF'}
        serializer = UserUpdateSerializer(cashier_user, data=data, partial=True)
        assert serializer.is_valid()
        user = serializer.save()
        
        assert user.role == 'INVENTORY_STAFF'


@pytest.mark.django_db
class TestChangePasswordSerializer:
    """Test cases for ChangePasswordSerializer"""
    
    def test_valid_password_change(self):
        """Test valid password change data"""
        data = {
            'old_password': 'oldpassword123',
            'new_password': 'newpassword123'
        }
        serializer = ChangePasswordSerializer(data=data)
        assert serializer.is_valid()
    
    def test_short_new_password_fails(self):
        """Test new password minimum length"""
        data = {
            'old_password': 'oldpassword123',
            'new_password': 'short'
        }
        serializer = ChangePasswordSerializer(data=data)
        assert not serializer.is_valid()
        assert 'new_password' in serializer.errors


# ============== Permission Tests ==============

@pytest.mark.django_db
class TestPermissions:
    """Test cases for custom permissions"""
    
    def test_is_admin_permission(self, admin_user, inventory_staff_user, cashier_user, viewer_user):
        """Test IsAdmin permission"""
        permission = IsAdmin()
        
        class MockRequest:
            def __init__(self, user):
                self.user = user
        
        assert permission.has_permission(MockRequest(admin_user), None)
        assert not permission.has_permission(MockRequest(inventory_staff_user), None)
        assert not permission.has_permission(MockRequest(cashier_user), None)
        assert not permission.has_permission(MockRequest(viewer_user), None)
    
    def test_is_inventory_staff_or_admin_permission(self, admin_user, inventory_staff_user, cashier_user, viewer_user):
        """Test IsInventoryStaffOrAdmin permission"""
        permission = IsInventoryStaffOrAdmin()
        
        class MockRequest:
            def __init__(self, user):
                self.user = user
        
        assert permission.has_permission(MockRequest(admin_user), None)
        assert permission.has_permission(MockRequest(inventory_staff_user), None)
        assert not permission.has_permission(MockRequest(cashier_user), None)
        assert not permission.has_permission(MockRequest(viewer_user), None)
    
    def test_is_cashier_or_above_permission(self, admin_user, inventory_staff_user, cashier_user, viewer_user):
        """Test IsCashierOrAbove permission"""
        permission = IsCashierOrAbove()
        
        class MockRequest:
            def __init__(self, user):
                self.user = user
        
        assert permission.has_permission(MockRequest(admin_user), None)
        assert permission.has_permission(MockRequest(inventory_staff_user), None)
        assert permission.has_permission(MockRequest(cashier_user), None)
        assert not permission.has_permission(MockRequest(viewer_user), None)
    
    def test_can_delete_products_permission(self, admin_user, inventory_staff_user, cashier_user, viewer_user):
        """Test CanDeleteProducts permission"""
        permission = CanDeleteProducts()
        
        class MockDeleteRequest:
            method = 'DELETE'
            def __init__(self, user):
                self.user = user
        
        class MockGetRequest:
            method = 'GET'
            def __init__(self, user):
                self.user = user
        
        assert permission.has_permission(MockDeleteRequest(admin_user), None)
        assert not permission.has_permission(MockDeleteRequest(inventory_staff_user), None)
        assert not permission.has_permission(MockDeleteRequest(cashier_user), None)
        assert permission.has_permission(MockGetRequest(viewer_user), None)
    
    def test_can_adjust_stock_permission(self, admin_user, inventory_staff_user, cashier_user, viewer_user):
        """Test CanAdjustStock permission"""
        permission = CanAdjustStock()
        
        class MockRequest:
            def __init__(self, user):
                self.user = user
        
        assert permission.has_permission(MockRequest(admin_user), None)
        assert permission.has_permission(MockRequest(inventory_staff_user), None)
        assert not permission.has_permission(MockRequest(cashier_user), None)
        assert not permission.has_permission(MockRequest(viewer_user), None)


# ============== Authentication API Tests ==============

@pytest.mark.django_db
class TestAuthenticationAPI:
    """Test authentication endpoints"""

    def test_login_success(self, api_client, admin_user):
        """Test successful login returns tokens"""
        response = api_client.post('/api/auth/login/', {
            'username': 'admin',
            'password': 'testpass123'
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access_token' in response.data
        assert 'refresh_token' in response.data
        assert 'user' in response.data
        assert response.data['token_type'] == 'Bearer'

    def test_login_invalid_credentials(self, api_client, admin_user):
        """Test login with wrong password fails"""
        response = api_client.post('/api/auth/login/', {
            'username': 'admin',
            'password': 'wrongpassword'
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_missing_credentials(self, api_client):
        """Test login without credentials fails"""
        response = api_client.post('/api/auth/login/', {})
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_inactive_employee(self, api_client, partner, oauth_application):
        """Test login with inactive employee fails"""
        user = User.objects.create_user(
            username='inactive_login',
            password='testpass123',
            is_active_employee=False,
            partner=partner
        )
        
        response = api_client.post('/api/auth/login/', {
            'username': 'inactive_login',
            'password': 'testpass123'
        })
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_logout_success(self, admin_client):
        """Test successful logout"""
        response = admin_client.post('/api/auth/logout/')
        
        assert response.status_code == status.HTTP_200_OK

    def test_current_user(self, admin_client, admin_user):
        """Test getting current user info"""
        response = admin_client.get('/api/auth/me/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['username'] == admin_user.username

    def test_change_password_success(self, admin_client, admin_user):
        """Test successful password change"""
        response = admin_client.post('/api/auth/change-password/', {
            'old_password': 'testpass123',
            'new_password': 'newpassword456'
        })
        
        assert response.status_code == status.HTTP_200_OK
        admin_user.refresh_from_db()
        assert admin_user.check_password('newpassword456')

    def test_change_password_wrong_old_password(self, admin_client):
        """Test change password with wrong old password"""
        response = admin_client.post('/api/auth/change-password/', {
            'old_password': 'wrongpassword',
            'new_password': 'newpassword123'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============== User Management API Tests ==============

@pytest.mark.django_db
class TestUserManagementAPI:
    """Test user management endpoints"""

    def test_admin_can_list_users(self, admin_client, admin_user, cashier_user):
        """Test admin can list users in their partner"""
        response = admin_client.get('/api/auth/')
        
        assert response.status_code == status.HTTP_200_OK
        users = response.data if isinstance(response.data, list) else response.data.get('results', [])
        usernames = [u['username'] for u in users]
        assert admin_user.username in usernames

    def test_super_admin_can_list_all_users(self, super_admin_client, admin_user, partner2_admin):
        """Test super admin can see all users"""
        response = super_admin_client.get('/api/auth/')
        
        assert response.status_code == status.HTTP_200_OK
        users = response.data if isinstance(response.data, list) else response.data.get('results', [])
        usernames = [u['username'] for u in users]
        assert admin_user.username in usernames
        assert partner2_admin.username in usernames

    def test_admin_can_create_user(self, admin_client, partner):
        """Test admin can create user in their partner"""
        response = admin_client.post('/api/auth/', {
            'username': 'newuser_admin',
            'email': 'newuser@test.com',
            'password': 'testpass123',
            'role': 'CASHIER'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get(username='newuser_admin')
        assert user.partner == partner

    def test_non_admin_cannot_manage_users(self, viewer_client):
        """Test non-admin users cannot list users"""
        response = viewer_client.get('/api/auth/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_user_as_admin(self, admin_client, cashier_user):
        """Test admin can update user"""
        response = admin_client.patch(f'/api/auth/{cashier_user.id}/', {
            'role': 'INVENTORY_STAFF'
        })
        
        assert response.status_code == status.HTTP_200_OK

    def test_delete_user_as_admin(self, admin_client, partner):
        """Test admin can delete user"""
        user_to_delete = User.objects.create_user(
            username='todelete',
            password='pass123',
            role=User.Role.VIEWER,
            partner=partner
        )
        
        response = admin_client.delete(f'/api/auth/{user_to_delete.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT


# ============== Partner Management API Tests ==============

@pytest.mark.django_db
class TestPartnerManagementAPI:
    """Test partner management endpoints (Super Admin only)"""

    def test_super_admin_can_list_partners(self, super_admin_client, partner, partner2):
        """Test super admin can list all partners"""
        response = super_admin_client.get('/api/auth/partners/')
        
        assert response.status_code == status.HTTP_200_OK
        partners = response.data if isinstance(response.data, list) else response.data.get('results', [])
        codes = [p['code'] for p in partners]
        assert partner.code in codes
        assert partner2.code in codes

    def test_non_super_admin_cannot_list_partners(self, admin_client):
        """Test regular admin cannot list partners"""
        response = admin_client.get('/api/auth/partners/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_super_admin_can_create_partner(self, super_admin_client):
        """Test super admin can create a partner"""
        response = super_admin_client.post('/api/auth/partners/', {
            'name': 'New Partner',
            'code': 'NEWPARTNER001',
            'contact_email': 'new@partner.com',
            'is_active': True
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        assert Partner.objects.filter(code='NEWPARTNER001').exists()

    def test_create_partner_duplicate_code_fails(self, super_admin_client, partner):
        """Test creating partner with duplicate code fails"""
        response = super_admin_client.post('/api/auth/partners/', {
            'name': 'Duplicate Partner',
            'code': partner.code,
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_super_admin_can_update_partner(self, super_admin_client, partner):
        """Test super admin can update partner"""
        response = super_admin_client.patch(f'/api/auth/partners/{partner.id}/', {
            'contact_phone': '9876543210'
        })
        
        assert response.status_code == status.HTTP_200_OK
        partner.refresh_from_db()
        assert partner.contact_phone == '9876543210'

    def test_search_partners(self, super_admin_client, partner):
        """Test searching partners by name or code"""
        response = super_admin_client.get(f'/api/auth/partners/?search={partner.code}')
        
        assert response.status_code == status.HTTP_200_OK
        partners = response.data if isinstance(response.data, list) else response.data.get('results', [])
        assert any(p['code'] == partner.code for p in partners)

    def test_filter_active_partners(self, super_admin_client, partner, inactive_partner):
        """Test filtering partners by active status"""
        response = super_admin_client.get('/api/auth/partners/?is_active=true')
        
        assert response.status_code == status.HTTP_200_OK
        partners = response.data if isinstance(response.data, list) else response.data.get('results', [])
        for p in partners:
            assert p['is_active'] is True


# ============== Impersonation API Tests ==============

@pytest.mark.django_db
class TestImpersonationAPI:
    """Test impersonation endpoints"""

    def test_super_admin_can_impersonate(self, super_admin_client, partner):
        """Test super admin can impersonate a partner"""
        response = super_admin_client.post(f'/api/auth/impersonate/{partner.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access_token' in response.data
        assert 'impersonating' in response.data
        assert response.data['impersonating']['id'] == partner.id

    def test_cannot_impersonate_inactive_partner(self, super_admin_client, inactive_partner):
        """Test cannot impersonate inactive partner"""
        response = super_admin_client.post(f'/api/auth/impersonate/{inactive_partner.id}/')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'inactive' in response.data['error'].lower()

    def test_non_super_admin_cannot_impersonate(self, admin_client, partner2):
        """Test regular admin cannot impersonate"""
        response = admin_client.post(f'/api/auth/impersonate/{partner2.id}/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_exit_impersonation(self, impersonation_client):
        """Test exiting impersonation mode"""
        response = impersonation_client.post('/api/auth/exit-impersonation/')
        
        assert response.status_code == status.HTTP_200_OK

    def test_exit_impersonation_when_not_impersonating(self, admin_client):
        """Test exit impersonation when not impersonating returns error"""
        response = admin_client.post('/api/auth/exit-impersonation/')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_impersonation_status_when_impersonating(self, impersonation_client, partner):
        """Test checking impersonation status when impersonating"""
        response = impersonation_client.get('/api/auth/impersonation-status/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_impersonating'] is True
        assert response.data['partner']['id'] == partner.id

    def test_impersonation_status_when_not_impersonating(self, admin_client):
        """Test checking impersonation status when not impersonating"""
        response = admin_client.get('/api/auth/impersonation-status/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_impersonating'] is False


# ============== Multi-Tenant Data Isolation Tests ==============

@pytest.mark.django_db
class TestMultiTenantIsolation:
    """Test data isolation between partners"""

    def test_partner_admin_cannot_see_other_partner_users(self, admin_client, partner2_admin):
        """Test admin cannot see users from other partners"""
        response = admin_client.get(f'/api/auth/{partner2_admin.id}/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_impersonation_provides_partner_context(self, impersonation_client, partner, category):
        """Test impersonation provides correct partner context for data"""
        response = impersonation_client.get('/api/inventory/categories/')
        
        assert response.status_code == status.HTTP_200_OK
        categories = response.data if isinstance(response.data, list) else response.data.get('results', [])
        names = [c['name'] for c in categories]
        assert category.name in names

    def test_impersonation_isolates_from_other_partners(self, impersonation_client, partner2_category):
        """Test impersonation cannot access other partner's data"""
        response = impersonation_client.get(f'/api/inventory/categories/{partner2_category.id}/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_impersonation_creates_data_for_partner(self, impersonation_client, partner):
        """Test data created during impersonation belongs to impersonated partner"""
        from inventory.models import Product, Category
        
        cat = Category.objects.create(partner=partner, name='Impersonation Test Category')
        
        response = impersonation_client.post('/api/inventory/products/', {
            'sku': 'IMP-SKU-001',
            'name': 'Impersonation Product',
            'category': cat.id,
            'cost_price': '50.00',
            'selling_price': '75.00'
        })
        
        assert response.status_code == status.HTTP_201_CREATED, f"Expected 201, got {response.status_code}: {response.data}"
        product = Product.objects.get(sku='IMP-SKU-001')
        assert product.partner == partner


# ============== Role Permission API Tests ==============

@pytest.mark.django_db
class TestRolePermissions:
    """Test role-based permissions"""

    def test_admin_has_full_access(self, admin_client):
        """Test admin role has full access within partner"""
        response = admin_client.get('/api/auth/')
        assert response.status_code == status.HTTP_200_OK

    def test_inventory_staff_can_manage_inventory(self, inventory_client, product):
        """Test inventory staff can manage inventory"""
        response = inventory_client.patch(f'/api/inventory/products/{product.id}/', {
            'minimum_stock_level': 30
        })
        assert response.status_code == status.HTTP_200_OK

    def test_cashier_can_create_sales(self, cashier_client, product):
        """Test cashier can create sales"""
        response = cashier_client.post('/api/sales/', {
            'payment_method': 'CASH',
            'items': [
                {
                    'product': product.id,
                    'quantity': 1,
                    'unit_price': str(product.selling_price)
                }
            ]
        }, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED

    def test_viewer_is_read_only(self, viewer_client, product, category):
        """Test viewer can only read, not write"""
        response = viewer_client.get('/api/inventory/products/')
        assert response.status_code == status.HTTP_200_OK
        
        response = viewer_client.post('/api/inventory/products/', {
            'sku': 'VIEWER-001',
            'name': 'Viewer Product',
            'category': category.id,
            'cost_price': '50.00',
            'selling_price': '75.00'
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN

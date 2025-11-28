"""
Comprehensive Unit Tests for Users Module
Tests for: User model, permissions, serializers, views, and authentication
"""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from users.permissions import (
    IsAdmin, IsInventoryStaffOrAdmin, IsCashierOrAbove,
    CanDeleteProducts, CanAdjustStock
)
from users.serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer, ChangePasswordSerializer
)

User = get_user_model()


class UserModelTest(TestCase):
    """Test cases for User model"""
    
    def test_create_user(self):
        """Test creating a new user"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role=User.Role.CASHIER
        )
        
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.role, User.Role.CASHIER)
        self.assertTrue(user.check_password('testpass123'))
    
    def test_create_admin_user(self):
        """Test creating an admin user"""
        admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            role=User.Role.ADMIN
        )
        
        self.assertEqual(admin.role, User.Role.ADMIN)
        self.assertTrue(admin.is_admin)
    
    def test_create_inventory_staff(self):
        """Test creating inventory staff user"""
        staff = User.objects.create_user(
            username='inventory_staff',
            email='staff@example.com',
            password='staffpass123',
            role=User.Role.INVENTORY_STAFF
        )
        
        self.assertEqual(staff.role, User.Role.INVENTORY_STAFF)
        self.assertTrue(staff.is_inventory_staff)
    
    def test_create_cashier(self):
        """Test creating cashier user"""
        cashier = User.objects.create_user(
            username='cashier',
            email='cashier@example.com',
            password='cashierpass123',
            role=User.Role.CASHIER
        )
        
        self.assertEqual(cashier.role, User.Role.CASHIER)
        self.assertTrue(cashier.is_cashier)
    
    def test_create_viewer(self):
        """Test creating viewer user"""
        viewer = User.objects.create_user(
            username='viewer',
            email='viewer@example.com',
            password='viewerpass123',
            role=User.Role.VIEWER
        )
        
        self.assertEqual(viewer.role, User.Role.VIEWER)
        self.assertTrue(viewer.is_viewer)
    
    def test_user_role_properties_admin(self):
        """Test admin user role properties"""
        admin = User.objects.create_user(
            username='admin',
            password='pass',
            role=User.Role.ADMIN
        )
        
        self.assertTrue(admin.is_admin)
        self.assertFalse(admin.is_inventory_staff)
        self.assertFalse(admin.is_cashier)
        self.assertFalse(admin.is_viewer)
    
    def test_user_role_properties_inventory_staff(self):
        """Test inventory staff user role properties"""
        staff = User.objects.create_user(
            username='staff',
            password='pass',
            role=User.Role.INVENTORY_STAFF
        )
        
        self.assertFalse(staff.is_admin)
        self.assertTrue(staff.is_inventory_staff)
        self.assertFalse(staff.is_cashier)
        self.assertFalse(staff.is_viewer)
    
    def test_user_role_properties_cashier(self):
        """Test cashier user role properties"""
        cashier = User.objects.create_user(
            username='cashier',
            password='pass',
            role=User.Role.CASHIER
        )
        
        self.assertFalse(cashier.is_admin)
        self.assertFalse(cashier.is_inventory_staff)
        self.assertTrue(cashier.is_cashier)
        self.assertFalse(cashier.is_viewer)
    
    def test_user_role_properties_viewer(self):
        """Test viewer user role properties"""
        viewer = User.objects.create_user(
            username='viewer',
            password='pass',
            role=User.Role.VIEWER
        )
        
        self.assertFalse(viewer.is_admin)
        self.assertFalse(viewer.is_inventory_staff)
        self.assertFalse(viewer.is_cashier)
        self.assertTrue(viewer.is_viewer)
    
    def test_user_str_representation(self):
        """Test user string representation"""
        user = User.objects.create_user(
            username='john',
            password='pass',
            role=User.Role.INVENTORY_STAFF
        )
        
        self.assertEqual(str(user), "john (Inventory Staff)")
    
    def test_user_with_employee_id(self):
        """Test user with employee ID"""
        user = User.objects.create_user(
            username='employee',
            password='pass',
            role=User.Role.CASHIER,
            employee_id='EMP-001'
        )
        
        self.assertEqual(user.employee_id, 'EMP-001')
    
    def test_user_is_active_employee(self):
        """Test user is_active_employee field"""
        active_user = User.objects.create_user(
            username='active',
            password='pass',
            role=User.Role.CASHIER,
            is_active_employee=True
        )
        inactive_user = User.objects.create_user(
            username='inactive',
            password='pass',
            role=User.Role.CASHIER,
            is_active_employee=False
        )
        
        self.assertTrue(active_user.is_active_employee)
        self.assertFalse(inactive_user.is_active_employee)
    
    def test_all_role_choices(self):
        """Test all role choices are valid"""
        roles = [
            (User.Role.ADMIN, 'Admin'),
            (User.Role.INVENTORY_STAFF, 'Inventory Staff'),
            (User.Role.CASHIER, 'Cashier'),
            (User.Role.VIEWER, 'Viewer'),
        ]
        
        for role_value, role_label in roles:
            user = User.objects.create_user(
                username=f'user_{role_value}',
                password='pass',
                role=role_value
            )
            self.assertEqual(user.role, role_value)


class UserSerializerTest(TestCase):
    """Test cases for User serializers"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            role=User.Role.CASHIER,
            phone='123-456-7890',
            employee_id='EMP-001'
        )
    
    def test_user_serializer_fields(self):
        """Test UserSerializer contains expected fields"""
        serializer = UserSerializer(self.user)
        expected_fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'phone', 'employee_id', 'is_active_employee',
            'is_active', 'date_joined', 'last_login'
        ]
        for field in expected_fields:
            self.assertIn(field, serializer.data)
    
    def test_user_serializer_data(self):
        """Test UserSerializer data is correct"""
        serializer = UserSerializer(self.user)
        self.assertEqual(serializer.data['username'], 'testuser')
        self.assertEqual(serializer.data['email'], 'test@example.com')
        self.assertEqual(serializer.data['role'], 'CASHIER')


class UserCreateSerializerTest(TestCase):
    """Test cases for UserCreateSerializer"""
    
    def test_valid_user_creation(self):
        """Test valid user creation"""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'securepass123',
            'first_name': 'New',
            'last_name': 'User',
            'role': 'CASHIER'
        }
        serializer = UserCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        
        self.assertEqual(user.username, 'newuser')
        self.assertTrue(user.check_password('securepass123'))
    
    def test_password_is_hashed(self):
        """Test password is properly hashed"""
        data = {
            'username': 'hashtest',
            'email': 'hash@example.com',
            'password': 'mypassword123',
            'role': 'CASHIER'
        }
        serializer = UserCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        
        # Password should be hashed, not plain text
        self.assertNotEqual(user.password, 'mypassword123')
        self.assertTrue(user.check_password('mypassword123'))
    
    def test_short_password_fails(self):
        """Test password minimum length validation"""
        data = {
            'username': 'shortpass',
            'email': 'short@example.com',
            'password': 'short',  # Too short
            'role': 'CASHIER'
        }
        serializer = UserCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)


class UserUpdateSerializerTest(TestCase):
    """Test cases for UserUpdateSerializer"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='updatetest',
            email='update@example.com',
            password='testpass123',
            role=User.Role.CASHIER
        )
    
    def test_update_user_email(self):
        """Test updating user email"""
        data = {'email': 'newemail@example.com'}
        serializer = UserUpdateSerializer(self.user, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        
        self.assertEqual(user.email, 'newemail@example.com')
    
    def test_update_user_role(self):
        """Test updating user role"""
        data = {'role': 'INVENTORY_STAFF'}
        serializer = UserUpdateSerializer(self.user, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        
        self.assertEqual(user.role, 'INVENTORY_STAFF')


class ChangePasswordSerializerTest(TestCase):
    """Test cases for ChangePasswordSerializer"""
    
    def test_valid_password_change(self):
        """Test valid password change data"""
        data = {
            'old_password': 'oldpassword123',
            'new_password': 'newpassword123'
        }
        serializer = ChangePasswordSerializer(data=data)
        self.assertTrue(serializer.is_valid())
    
    def test_short_new_password_fails(self):
        """Test new password minimum length"""
        data = {
            'old_password': 'oldpassword123',
            'new_password': 'short'
        }
        serializer = ChangePasswordSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('new_password', serializer.errors)


class UserAuthenticationAPITest(APITestCase):
    """Test cases for user authentication endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role=User.Role.CASHIER,
            is_active_employee=True
        )
        self.client = APIClient()
    
    def test_login_success(self):
        """Test successful login"""
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)
        self.assertIn('user', response.data)
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_login_missing_credentials(self):
        """Test login with missing credentials"""
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_login_inactive_employee(self):
        """Test login with inactive employee"""
        inactive_user = User.objects.create_user(
            username='inactive',
            password='testpass123',
            role=User.Role.CASHIER,
            is_active_employee=False
        )
        
        response = self.client.post('/api/auth/login/', {
            'username': 'inactive',
            'password': 'testpass123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_logout(self):
        """Test logout"""
        # First login
        login_response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        token = login_response.data['access_token']
        
        # Then logout
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.post('/api/auth/logout/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_get_current_user(self):
        """Test getting current user details"""
        login_response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        token = login_response.data['access_token']
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/auth/me/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')


class UserManagementAPITest(APITestCase):
    """Test cases for user management endpoints (Admin only)"""
    
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            role=User.Role.ADMIN,
            is_active_employee=True
        )
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='regularpass123',
            role=User.Role.CASHIER,
            is_active_employee=True
        )
        self.client = APIClient()
    
    def test_list_users_as_admin(self):
        """Test admin can list all users"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/auth/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_list_users_as_regular_user_fails(self):
        """Test regular user cannot list users"""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get('/api/auth/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_create_user_as_admin(self):
        """Test admin can create new user"""
        self.client.force_authenticate(user=self.admin_user)
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'newpass123',
            'role': 'CASHIER'
        }
        
        response = self.client.post('/api/auth/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_create_user_as_regular_user_fails(self):
        """Test regular user cannot create users"""
        self.client.force_authenticate(user=self.regular_user)
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'newpass123',
            'role': 'CASHIER'
        }
        
        response = self.client.post('/api/auth/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_update_user_as_admin(self):
        """Test admin can update user"""
        self.client.force_authenticate(user=self.admin_user)
        data = {'role': 'INVENTORY_STAFF'}
        
        response = self.client.patch(
            f'/api/auth/{self.regular_user.id}/',
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_delete_user_as_admin(self):
        """Test admin can delete user"""
        self.client.force_authenticate(user=self.admin_user)
        user_to_delete = User.objects.create_user(
            username='todelete',
            password='pass123',
            role=User.Role.VIEWER
        )
        
        response = self.client.delete(f'/api/auth/{user_to_delete.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
    
    def test_get_user_detail_as_admin(self):
        """Test admin can get user details"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(f'/api/auth/{self.regular_user.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'regular')


class ChangePasswordAPITest(APITestCase):
    """Test cases for change password endpoint"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='oldpassword123',
            role=User.Role.CASHIER,
            is_active_employee=True
        )
        self.client = APIClient()
    
    def test_change_password_success(self):
        """Test successful password change"""
        self.client.force_authenticate(user=self.user)
        data = {
            'old_password': 'oldpassword123',
            'new_password': 'newpassword123'
        }
        
        response = self.client.post('/api/auth/change-password/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify new password works
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpassword123'))
    
    def test_change_password_wrong_old_password(self):
        """Test change password with wrong old password"""
        self.client.force_authenticate(user=self.user)
        data = {
            'old_password': 'wrongpassword',
            'new_password': 'newpassword123'
        }
        
        response = self.client.post('/api/auth/change-password/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_change_password_unauthenticated(self):
        """Test change password when not authenticated"""
        data = {
            'old_password': 'oldpassword123',
            'new_password': 'newpassword123'
        }
        
        response = self.client.post('/api/auth/change-password/', data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PermissionsTest(TestCase):
    """Test cases for custom permissions"""
    
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            password='pass',
            role=User.Role.ADMIN
        )
        self.inventory_staff = User.objects.create_user(
            username='staff',
            password='pass',
            role=User.Role.INVENTORY_STAFF
        )
        self.cashier = User.objects.create_user(
            username='cashier',
            password='pass',
            role=User.Role.CASHIER
        )
        self.viewer = User.objects.create_user(
            username='viewer',
            password='pass',
            role=User.Role.VIEWER
        )
    
    def test_is_admin_permission(self):
        """Test IsAdmin permission"""
        permission = IsAdmin()
        
        # Mock request objects
        class MockRequest:
            def __init__(self, user):
                self.user = user
        
        self.assertTrue(permission.has_permission(MockRequest(self.admin), None))
        self.assertFalse(permission.has_permission(MockRequest(self.inventory_staff), None))
        self.assertFalse(permission.has_permission(MockRequest(self.cashier), None))
        self.assertFalse(permission.has_permission(MockRequest(self.viewer), None))
    
    def test_is_inventory_staff_or_admin_permission(self):
        """Test IsInventoryStaffOrAdmin permission"""
        permission = IsInventoryStaffOrAdmin()
        
        class MockRequest:
            def __init__(self, user):
                self.user = user
        
        self.assertTrue(permission.has_permission(MockRequest(self.admin), None))
        self.assertTrue(permission.has_permission(MockRequest(self.inventory_staff), None))
        self.assertFalse(permission.has_permission(MockRequest(self.cashier), None))
        self.assertFalse(permission.has_permission(MockRequest(self.viewer), None))
    
    def test_is_cashier_or_above_permission(self):
        """Test IsCashierOrAbove permission"""
        permission = IsCashierOrAbove()
        
        class MockRequest:
            def __init__(self, user):
                self.user = user
        
        self.assertTrue(permission.has_permission(MockRequest(self.admin), None))
        self.assertTrue(permission.has_permission(MockRequest(self.inventory_staff), None))
        self.assertTrue(permission.has_permission(MockRequest(self.cashier), None))
        self.assertFalse(permission.has_permission(MockRequest(self.viewer), None))
    
    def test_can_delete_products_permission(self):
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
        
        # Only admin can delete
        self.assertTrue(permission.has_permission(MockDeleteRequest(self.admin), None))
        self.assertFalse(permission.has_permission(MockDeleteRequest(self.inventory_staff), None))
        self.assertFalse(permission.has_permission(MockDeleteRequest(self.cashier), None))
        
        # All can GET
        self.assertTrue(permission.has_permission(MockGetRequest(self.viewer), None))
    
    def test_can_adjust_stock_permission(self):
        """Test CanAdjustStock permission"""
        permission = CanAdjustStock()
        
        class MockRequest:
            def __init__(self, user):
                self.user = user
        
        self.assertTrue(permission.has_permission(MockRequest(self.admin), None))
        self.assertTrue(permission.has_permission(MockRequest(self.inventory_staff), None))
        self.assertFalse(permission.has_permission(MockRequest(self.cashier), None))
        self.assertFalse(permission.has_permission(MockRequest(self.viewer), None))

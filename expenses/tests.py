"""
Comprehensive tests for Expenses Module.
Tests for: Expense Categories, Expenses, Stats, and multi-tenant isolation.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from rest_framework import status
from expenses.models import ExpenseCategory, Expense


# ============== ExpenseCategory Model Tests ==============

@pytest.mark.django_db
class TestExpenseCategoryModel:
    """Test ExpenseCategory model"""
    
    def test_create_expense_category(self, partner):
        """Test creating an expense category"""
        category = ExpenseCategory.objects.create(
            partner=partner,
            name='Office Supplies',
            description='General office supplies'
        )
        
        assert category.name == 'Office Supplies'
        assert str(category) == 'Office Supplies'
    
    def test_expense_category_ordering(self, partner):
        """Test expense categories are ordered by name"""
        ExpenseCategory.objects.create(partner=partner, name='Zebra')
        ExpenseCategory.objects.create(partner=partner, name='Alpha')
        
        categories = list(ExpenseCategory.objects.filter(partner=partner))
        assert categories[0].name == 'Alpha'
        assert categories[1].name == 'Zebra'


# ============== Expense Model Tests ==============

@pytest.mark.django_db
class TestExpenseModel:
    """Test Expense model"""
    
    def test_create_expense(self, partner, expense_category, admin_user):
        """Test creating an expense"""
        expense = Expense.objects.create(
            partner=partner,
            title='Office Chair',
            category=expense_category,
            amount=Decimal('150.00'),
            description='New ergonomic chair',
            expense_date=date.today(),
            created_by=admin_user
        )
        
        assert expense.amount == Decimal('150.00')
        assert expense.title == 'Office Chair'
        assert expense.category == expense_category
    
    def test_expense_str_representation(self, partner, expense_category, admin_user):
        """Test expense string representation"""
        expense = Expense.objects.create(
            partner=partner,
            title='Test Expense',
            category=expense_category,
            amount=Decimal('50.00'),
            expense_date=date.today(),
            created_by=admin_user
        )
        
        assert 'Test Expense' in str(expense)
        assert '50.00' in str(expense) or '50' in str(expense)
    
    def test_expense_with_receipt(self, partner, expense_category, admin_user):
        """Test expense with receipt number"""
        expense = Expense.objects.create(
            partner=partner,
            title='Supplies Purchase',
            category=expense_category,
            amount=Decimal('500.00'),
            description='Monthly supplies',
            expense_date=date.today(),
            receipt_number='REC-001',
            vendor='Office Depot',
            created_by=admin_user
        )
        
        assert expense.receipt_number == 'REC-001'
        assert expense.vendor == 'Office Depot'


# ============== ExpenseCategory API Tests ==============

@pytest.mark.django_db
class TestExpenseCategoryListAPI:
    """Test expense category listing endpoint"""

    def test_list_expense_categories(self, admin_client, expense_category):
        """Test listing expense categories"""
        response = admin_client.get('/api/expenses/categories/')
        
        assert response.status_code == status.HTTP_200_OK
        categories = response.data if isinstance(response.data, list) else response.data.get('results', [])
        assert len(categories) >= 1

    def test_list_expense_categories_partner_isolation(self, admin_client, expense_category, partner2):
        """Test expense categories are filtered by partner"""
        partner2_cat = ExpenseCategory.objects.create(
            partner=partner2,
            name='Partner2 Expense Category'
        )
        
        response = admin_client.get('/api/expenses/categories/')
        
        categories = response.data if isinstance(response.data, list) else response.data.get('results', [])
        names = [c['name'] for c in categories]
        assert expense_category.name in names
        assert partner2_cat.name not in names

    def test_impersonation_sees_correct_partner_categories(self, impersonation_client, expense_category, partner2):
        """Test impersonation shows impersonated partner's expense categories"""
        partner2_cat = ExpenseCategory.objects.create(
            partner=partner2,
            name='Partner2 Category Hidden'
        )
        
        response = impersonation_client.get('/api/expenses/categories/')
        
        assert response.status_code == status.HTTP_200_OK
        categories = response.data if isinstance(response.data, list) else response.data.get('results', [])
        names = [c['name'] for c in categories]
        assert expense_category.name in names
        assert partner2_cat.name not in names

    def test_super_admin_must_impersonate(self, super_admin_client):
        """Super admin without impersonation cannot access tenant expense categories"""
        response = super_admin_client.get('/api/expenses/categories/')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'impersonate' in str(response.data.get('detail', '')).lower()


@pytest.mark.django_db
class TestExpenseCategoryCreateAPI:
    """Test expense category creation endpoint"""

    def test_create_expense_category_success(self, admin_client, partner):
        """Test creating an expense category"""
        response = admin_client.post('/api/expenses/categories/', {
            'name': 'Travel',
            'description': 'Business travel expenses'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Travel'
        category = ExpenseCategory.objects.get(id=response.data['id'])
        assert category.partner == partner

    def test_create_expense_category_duplicate_name_fails(self, admin_client, expense_category):
        """Test duplicate category name in same partner fails"""
        response = admin_client.post('/api/expenses/categories/', {
            'name': expense_category.name
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_expense_category_same_name_different_partner_ok(self, partner2_client, expense_category):
        """Test different partners can have same expense category name"""
        response = partner2_client.post('/api/expenses/categories/', {
            'name': expense_category.name,
            'description': 'Different partner'
        })
        
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestExpenseCategoryDetailAPI:
    """Test expense category detail endpoints"""

    def test_get_expense_category_detail(self, admin_client, expense_category):
        """Test getting expense category details"""
        response = admin_client.get(f'/api/expenses/categories/{expense_category.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == expense_category.name

    def test_update_expense_category(self, admin_client, expense_category):
        """Test updating expense category"""
        response = admin_client.patch(f'/api/expenses/categories/{expense_category.id}/', {
            'description': 'Updated description'
        })
        
        assert response.status_code == status.HTTP_200_OK
        expense_category.refresh_from_db()
        assert expense_category.description == 'Updated description'

    def test_delete_expense_category_without_expenses(self, admin_client, partner):
        """Test deleting expense category without expenses"""
        cat = ExpenseCategory.objects.create(partner=partner, name='Deletable')
        
        response = admin_client.delete(f'/api/expenses/categories/{cat.id}/')
        
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_cannot_access_other_partner_expense_category(self, admin_client, partner2):
        """Test cannot access another partner's expense category"""
        partner2_cat = ExpenseCategory.objects.create(
            partner=partner2, 
            name='Hidden Category'
        )
        
        response = admin_client.get(f'/api/expenses/categories/{partner2_cat.id}/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ============== Expense API Tests ==============

@pytest.mark.django_db
class TestExpenseListAPI:
    """Test expense listing endpoint"""

    def test_list_expenses(self, admin_client, expense):
        """Test listing expenses"""
        response = admin_client.get('/api/expenses/')
        
        assert response.status_code == status.HTTP_200_OK
        expenses = response.data if isinstance(response.data, list) else response.data.get('results', [])
        assert len(expenses) >= 1

    def test_list_expenses_partner_isolation(self, admin_client, expense, partner2, partner2_admin):
        """Test expenses are filtered by partner"""
        partner2_cat = ExpenseCategory.objects.create(
            partner=partner2, 
            name='P2 Category'
        )
        partner2_expense = Expense.objects.create(
            partner=partner2,
            category=partner2_cat,
            amount=Decimal('100.00'),
            expense_date=date.today(),
            created_by=partner2_admin
        )
        
        response = admin_client.get('/api/expenses/')
        
        expenses = response.data if isinstance(response.data, list) else response.data.get('results', [])
        expense_ids = [e['id'] for e in expenses]
        assert expense.id in expense_ids
        assert partner2_expense.id not in expense_ids

    def test_filter_expenses_by_category(self, admin_client, expense, expense_category):
        """Test filtering expenses by category"""
        response = admin_client.get(f'/api/expenses/?category={expense_category.id}')
        
        assert response.status_code == status.HTTP_200_OK
        expenses = response.data if isinstance(response.data, list) else response.data.get('results', [])
        for e in expenses:
            assert e['category'] == expense_category.id

    def test_filter_expenses_by_date_range(self, admin_client, expense):
        """Test filtering expenses by date range"""
        today = date.today()
        start = (today - timedelta(days=7)).isoformat()
        end = today.isoformat()
        
        response = admin_client.get(f'/api/expenses/?start_date={start}&end_date={end}')
        
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestExpenseCreateAPI:
    """Test expense creation endpoint"""

    def test_create_expense_success(self, admin_client, expense_category, partner, admin_user):
        """Test creating an expense"""
        response = admin_client.post('/api/expenses/', {
            'title': 'New Office Chair',
            'category': expense_category.id,
            'amount': '200.00',
            'description': 'Ergonomic office chair',
            'expense_date': str(date.today())
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['amount'] == '200.00'
        # Get the expense by title since create serializer may not return id
        expense = Expense.objects.get(title='New Office Chair', partner=partner)
        assert expense.partner == partner
        assert expense.created_by == admin_user

    def test_create_expense_with_vendor(self, admin_client, expense_category):
        """Test creating an expense with vendor"""
        response = admin_client.post('/api/expenses/', {
            'title': 'Monthly Rent',
            'category': expense_category.id,
            'amount': '1000.00',
            'description': 'Office rent',
            'expense_date': str(date.today()),
            'vendor': 'ABC Properties'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['vendor'] == 'ABC Properties'

    def test_create_expense_with_receipt(self, admin_client, expense_category):
        """Test creating expense with receipt attachment"""
        response = admin_client.post('/api/expenses/', {
            'title': 'Supplies',
            'category': expense_category.id,
            'amount': '50.00',
            'expense_date': str(date.today()),
            'receipt_number': 'REC-001'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['receipt_number'] == 'REC-001'

    def test_create_expense_negative_amount_fails(self, admin_client, expense_category):
        """Test negative amount is rejected"""
        response = admin_client.post('/api/expenses/', {
            'title': 'Bad Expense',
            'category': expense_category.id,
            'amount': '-50.00',
            'expense_date': str(date.today())
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_expense_zero_amount_fails(self, admin_client, expense_category):
        """Test zero amount is rejected"""
        response = admin_client.post('/api/expenses/', {
            'title': 'Zero Expense',
            'category': expense_category.id,
            'amount': '0.00',
            'expense_date': str(date.today())
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestExpenseDetailAPI:
    """Test expense detail endpoints"""

    def test_get_expense_detail(self, admin_client, expense):
        """Test getting expense details"""
        response = admin_client.get(f'/api/expenses/{expense.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert Decimal(response.data['amount']) == expense.amount

    def test_update_expense_amount(self, admin_client, expense):
        """Test updating expense amount"""
        response = admin_client.patch(f'/api/expenses/{expense.id}/', {
            'amount': '300.00'
        })
        
        assert response.status_code == status.HTTP_200_OK
        expense.refresh_from_db()
        assert expense.amount == Decimal('300.00')

    def test_update_expense_description(self, admin_client, expense):
        """Test updating expense description"""
        response = admin_client.patch(f'/api/expenses/{expense.id}/', {
            'description': 'Updated description'
        })
        
        assert response.status_code == status.HTTP_200_OK
        expense.refresh_from_db()
        assert expense.description == 'Updated description'

    def test_delete_expense(self, admin_client, expense):
        """Test deleting an expense"""
        expense_id = expense.id
        
        response = admin_client.delete(f'/api/expenses/{expense_id}/')
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Expense.objects.filter(id=expense_id).exists()

    def test_cannot_access_other_partner_expense(self, admin_client, partner2, partner2_admin):
        """Test cannot access another partner's expense"""
        partner2_cat = ExpenseCategory.objects.create(
            partner=partner2, 
            name='P2 Category'
        )
        partner2_expense = Expense.objects.create(
            partner=partner2,
            category=partner2_cat,
            amount=Decimal('100.00'),
            expense_date=date.today(),
            created_by=partner2_admin
        )
        
        response = admin_client.get(f'/api/expenses/{partner2_expense.id}/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ============== Expense Stats API Tests ==============

@pytest.mark.django_db
class TestExpenseStatsAPI:
    """Test expense statistics endpoint"""

    def test_expense_stats_returns_totals(self, admin_client, expense, expense_category, partner, admin_user):
        """Test expense stats returns correct totals"""
        # Create additional expenses
        Expense.objects.create(
            partner=partner,
            category=expense_category,
            amount=Decimal('200.00'),
            expense_date=date.today(),
            created_by=admin_user
        )
        
        response = admin_client.get('/api/expenses/stats/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'total_expenses' in response.data
        assert Decimal(response.data['total_expenses']) >= Decimal('200.00')

    def test_expense_stats_by_category(self, admin_client, expense_category, partner, admin_user):
        """Test expense stats includes breakdown by category"""
        Expense.objects.create(
            partner=partner,
            title='Category Test Expense',
            category=expense_category,
            amount=Decimal('100.00'),
            expense_date=date.today(),
            created_by=admin_user
        )
        
        # Stats endpoint includes by_category breakdown
        response = admin_client.get('/api/expenses/stats/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'by_category' in response.data
        assert isinstance(response.data['by_category'], list)

    def test_expense_stats_with_date_filter(self, admin_client, expense):
        """Test expense stats with date filtering"""
        today = date.today()
        start = (today - timedelta(days=30)).isoformat()
        end = today.isoformat()
        
        response = admin_client.get(f'/api/expenses/stats/?start_date={start}&end_date={end}')
        
        assert response.status_code == status.HTTP_200_OK

    def test_expense_stats_partner_isolation(self, admin_client, expense, partner2, partner2_admin):
        """Test expense stats only include own partner's data"""
        partner2_cat = ExpenseCategory.objects.create(
            partner=partner2,
            name='P2 Category'
        )
        # Create large expense in partner2
        Expense.objects.create(
            partner=partner2,
            title='Large P2 Expense',
            category=partner2_cat,
            amount=Decimal('10000.00'),
            expense_date=date.today(),
            created_by=partner2_admin
        )
        
        response = admin_client.get('/api/expenses/stats/')
        
        assert response.status_code == status.HTTP_200_OK
        # Partner1's total should not include partner2's 10000
        assert Decimal(response.data['total_expenses']) < Decimal('10000.00')


# ============== Expense Role-Based Access Tests ==============

@pytest.mark.django_db
class TestExpenseRoleAccess:
    """Test role-based access control for expenses"""

    def test_admin_has_full_access(self, admin_client, expense_category):
        """Test admin can create expenses"""
        response = admin_client.post('/api/expenses/', {
            'title': 'Admin Expense',
            'category': expense_category.id,
            'amount': '100.00',
            'expense_date': str(date.today())
        })
        assert response.status_code == status.HTTP_201_CREATED

    def test_inventory_staff_can_manage_expenses(self, inventory_client, expense_category):
        """Test inventory staff can manage expenses (any authenticated user can)"""
        response = inventory_client.post('/api/expenses/', {
            'title': 'Inventory Staff Expense',
            'category': expense_category.id,
            'amount': '100.00',
            'expense_date': str(date.today())
        })
        assert response.status_code == status.HTTP_201_CREATED

    def test_cashier_can_manage_expenses(self, cashier_client, expense_category):
        """Test cashier can manage expenses (any authenticated user can)"""
        response = cashier_client.post('/api/expenses/', {
            'title': 'Cashier Expense',
            'category': expense_category.id,
            'amount': '100.00',
            'expense_date': str(date.today())
        })
        assert response.status_code == status.HTTP_201_CREATED

    def test_viewer_can_view_expenses(self, viewer_client, expense):
        """Test viewer can view expenses"""
        response = viewer_client.get('/api/expenses/')
        assert response.status_code == status.HTTP_200_OK

    def test_viewer_can_create_expenses(self, viewer_client, expense_category):
        """Test viewer can create expenses (any authenticated user can)"""
        response = viewer_client.post('/api/expenses/', {
            'title': 'Viewer Expense',
            'category': expense_category.id,
            'amount': '100.00',
            'expense_date': str(date.today())
        })
        assert response.status_code == status.HTTP_201_CREATED

    def test_viewer_can_update_expenses(self, viewer_client, expense):
        """Test viewer can update expenses (any authenticated user can)"""
        response = viewer_client.patch(f'/api/expenses/{expense.id}/', {
            'amount': '999.99'
        })
        assert response.status_code == status.HTTP_200_OK

    def test_viewer_can_delete_expenses(self, viewer_client, expense):
        """Test viewer can delete expenses (any authenticated user can)"""
        response = viewer_client.delete(f'/api/expenses/{expense.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT


# ============== Expense Impersonation Tests ==============

@pytest.mark.django_db
class TestExpenseImpersonation:
    """Test impersonation for expense management"""

    def test_impersonation_sees_correct_partner_expenses(self, impersonation_client, expense, partner2, partner2_admin):
        """Test impersonation shows impersonated partner's expenses"""
        partner2_cat = ExpenseCategory.objects.create(
            partner=partner2,
            name='P2 Category'
        )
        partner2_expense = Expense.objects.create(
            partner=partner2,
            title='Partner2 Expense',
            category=partner2_cat,
            amount=Decimal('100.00'),
            expense_date=date.today(),
            created_by=partner2_admin
        )
        
        response = impersonation_client.get('/api/expenses/')
        
        assert response.status_code == status.HTTP_200_OK
        expenses = response.data if isinstance(response.data, list) else response.data.get('results', [])
        expense_ids = [e['id'] for e in expenses]
        assert expense.id in expense_ids
        assert partner2_expense.id not in expense_ids

    def test_impersonation_creates_expense_for_correct_partner(self, impersonation_client, expense_category, partner):
        """Test impersonation creates expense for impersonated partner"""
        response = impersonation_client.post('/api/expenses/', {
            'title': 'Impersonation Expense',
            'category': expense_category.id,
            'amount': '75.00',
            'expense_date': str(date.today()),
            'description': 'Impersonation test'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        expense = Expense.objects.get(title='Impersonation Expense', partner=partner)
        assert expense.partner == partner

    def test_impersonation_expense_stats_correct_partner(self, impersonation_client, expense, partner2, partner2_admin):
        """Test impersonation stats show impersonated partner's data only"""
        # expense fixture creates 5000.00 for partner1
        partner1_total = expense.amount  # Should be 5000.00
        
        partner2_cat = ExpenseCategory.objects.create(
            partner=partner2,
            name='P2 Category'
        )
        Expense.objects.create(
            partner=partner2,
            title='Large Partner2 Expense',
            category=partner2_cat,
            amount=Decimal('10000.00'),  # This should NOT be included
            expense_date=date.today(),
            created_by=partner2_admin
        )
        
        response = impersonation_client.get('/api/expenses/stats/')
        
        assert response.status_code == status.HTTP_200_OK
        # Total should equal partner1's expense only (5000), not include partner2's 10000
        assert Decimal(response.data['total_expenses']) == partner1_total


# ============== Expense Unauthenticated Tests ==============

@pytest.mark.django_db
class TestExpenseUnauthenticated:
    """Test unauthenticated access is blocked"""

    def test_unauthenticated_cannot_list_expenses(self, api_client):
        """Test unauthenticated request is rejected"""
        response = api_client.get('/api/expenses/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated_cannot_list_expense_categories(self, api_client):
        """Test unauthenticated request is rejected"""
        response = api_client.get('/api/expenses/categories/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated_cannot_view_stats(self, api_client):
        """Test unauthenticated request is rejected"""
        response = api_client.get('/api/expenses/stats/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

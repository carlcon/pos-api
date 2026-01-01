#!/usr/bin/env python
"""
Test script to verify the new StoreInventory system is working correctly.
Run this after running migrations to test the complete flow.
"""

import os
import django
import pytest

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings')
django.setup()

from django.contrib.auth import get_user_model
from inventory.models import Product, StoreInventory, Category
from stores.models import Store
from users.models import Partner

User = get_user_model()


@pytest.mark.django_db
def test_inventory_system():
    """Test the inventory system"""
    print("\n" + "="*60)
    print("STORE INVENTORY SYSTEM TEST")
    print("="*60 + "\n")
    
    # Get demo partner
    try:
        partner = Partner.objects.get(code='DEMO')
        print(f"✓ Found partner: {partner.name} ({partner.code})")
    except Partner.DoesNotExist:
        print("✗ Demo partner (DEMO) not found. Please create it first.")
        return
    
    # Get stores
    stores = Store.objects.filter(partner=partner)
    if not stores.exists():
        print("✗ No stores found for demo partner. Please create stores first.")
        return
    
    print(f"✓ Found {stores.count()} store(s):")
    for store in stores:
        print(f"  - {store.name} ({store.code})")
    
    # Get products
    products = Product.objects.filter(partner=partner)[:5]
    if not products.exists():
        print("\n✗ No products found. Please create products first.")
        return
    
    print(f"\n✓ Found {products.count()} sample product(s):")
    for product in products:
        print(f"  - {product.sku}: {product.name}")
    
    # Check StoreInventory records
    print("\n" + "-"*60)
    print("STORE INVENTORY STATUS")
    print("-"*60)
    
    for store in stores:
        print(f"\n{store.name}:")
        inventories = StoreInventory.objects.filter(store=store).select_related('product')
        
        if not inventories.exists():
            print("  ⚠ No inventory records found for this store")
        else:
            total_stock = sum(inv.current_stock for inv in inventories)
            low_stock = inventories.filter(
                current_stock__lte=django.db.models.F('minimum_stock_level')
            ).count()
            
            print(f"  Total products: {inventories.count()}")
            print(f"  Total stock units: {total_stock}")
            print(f"  Low stock items: {low_stock}")
            
            print(f"\n  Sample inventory records:")
            for inv in inventories[:5]:
                status = "🔴 LOW" if inv.is_low_stock else "🟢 OK"
                print(f"    {status} {inv.product.sku}: {inv.current_stock} units (min: {inv.minimum_stock_level})")
    
    # Test aggregated stock
    print("\n" + "-"*60)
    print("AGGREGATED STOCK TEST")
    print("-"*60)
    
    test_product = products.first()
    print(f"\nProduct: {test_product.sku} - {test_product.name}")
    
    store_stocks = StoreInventory.objects.filter(product=test_product)
    print(f"\nStock by store:")
    total = 0
    for inv in store_stocks:
        print(f"  {inv.store.name}: {inv.current_stock} units")
        total += inv.current_stock
    
    print(f"\nTotal across all stores: {total} units")
    
    # Recommendations
    print("\n" + "="*60)
    print("RECOMMENDATIONS")
    print("="*60)
    
    all_inventories = StoreInventory.objects.all()
    if not all_inventories.exists():
        print("\n⚠ WARNING: No StoreInventory records found!")
        print("\nTo populate inventory, you can:")
        print("1. Run: python manage.py assign_products_to_stores --partner-code DEMO001")
        print("2. Or manually create inventory records via Django admin or API")
    else:
        print(f"\n✓ System has {all_inventories.count()} inventory records")
        
        empty_stores = stores.exclude(inventories__isnull=False).distinct()
        if empty_stores.exists():
            print(f"\n⚠ {empty_stores.count()} store(s) have no inventory:")
            for store in empty_stores:
                print(f"  - {store.name}")
    
    # Check for products without any inventory
    products_without_inventory = Product.objects.filter(
        partner=partner
    ).exclude(
        store_inventories__isnull=False
    ).distinct()
    
    if products_without_inventory.exists():
        print(f"\n⚠ {products_without_inventory.count()} product(s) have no inventory in any store:")
        for product in products_without_inventory[:5]:
            print(f"  - {product.sku}: {product.name}")
        if products_without_inventory.count() > 5:
            print(f"  ... and {products_without_inventory.count() - 5} more")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60 + "\n")


if __name__ == '__main__':
    test_inventory_system()

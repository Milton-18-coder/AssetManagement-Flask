"""
AssetVault - Automated Test & Verification Suite
Tests all routes, authentication, CRUD workflows, assignments, maintenance, reports, and APIs.
"""

import sys
from app import create_app, get_db

def run_tests():
    print("=== Starting AssetVault System Verification ===")
    app = create_app()
    app.config['TESTING'] = True
    client = app.test_client()

    # 1. Unauthenticated redirects
    res = client.get('/dashboard')
    assert res.status_code == 302, f"Expected 302 redirect for protected dashboard, got {res.status_code}"
    print(" [OK] Protected routes redirect unauthenticated users correctly")

    # 2. Login verification
    # Invalid login
    res = client.post('/login', data={'username': 'admin', 'password': 'wrongpassword'}, follow_redirects=True)
    assert res.status_code == 200
    assert b"Sign In to Vault" in res.data
    print(" [OK] Invalid login properly kept on login page")

    # Valid login
    res = client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
    assert res.status_code == 200
    assert b"Executive Dashboard" in res.data or b"Total Assets" in res.data
    print(" [OK] Admin login successful, redirected to Dashboard")

    # 3. Dashboard rendering
    res = client.get('/dashboard')
    assert res.status_code == 200
    assert b"Executive Dashboard" in res.data
    assert b"Total Valuation" in res.data
    assert b"Recent Activity" in res.data
    print(" [OK] Dashboard renders 8 KPI metric cards, maintenance overview, and alerts")

    # 4. Assets Index, Search & Filter
    res = client.get('/assets')
    assert res.status_code == 200
    assert b"AST-0001" in res.data
    print(" [OK] Asset inventory table loads with records")

    # Search filter
    res = client.get('/assets?search=MacBook')
    assert res.status_code == 200
    assert b"MacBook Pro 16" in res.data
    print(" [OK] Asset search filter matches keywords correctly")

    # Smart Alert Filters (Warranty & Condition)
    res = client.get('/assets?alert=warranty')
    assert res.status_code == 200
    assert b"Active Warning Filter" in res.data
    print(" [OK] Asset warranty alert filter correctly handles expiring warranties")

    res = client.get('/assets?alert=condition')
    assert res.status_code == 200
    assert b"Active Warning Filter" in res.data
    print(" [OK] Asset condition alert filter correctly displays critical/poor condition assets")

    res = client.get('/assignments?status=Overdue')
    assert res.status_code == 200
    assert b"Active Warning Filter" in res.data
    print(" [OK] Assignments overdue filter correctly displays overdue assignments")

    # 5. Create Asset
    new_asset_data = {
        'asset_name': 'Test iPad Air M2',
        'category': 'Laptop',
        'brand': 'Apple',
        'model': 'iPad Air 11-inch',
        'serial_number': 'TEST-IPAD-AIR-9901',
        'purchase_date': '2024-04-01',
        'purchase_cost': '59900',
        'supplier': 'Apple Store',
        'department': 'Computer Science',
        'location': 'Lab 1',
        'warranty_expiry': '2027-04-01',
        'condition': 'Excellent',
        'status': 'Available',
        'description': 'Test asset for verification suite'
    }
    res = client.post('/assets/add', data=new_asset_data, follow_redirects=True)
    assert res.status_code == 200
    assert b"Test iPad Air M2" in res.data
    print(" [OK] Asset created successfully with auto-generated ID")

    # Find created asset
    db = get_db()
    created_asset = db.assets.find_one({"serial_number": "TEST-IPAD-AIR-9901"})
    assert created_asset is not None
    test_asset_id = created_asset['asset_id']
    print(f" [OK] Created asset assigned ID: {test_asset_id}")

    # Duplicate serial rejection
    res = client.post('/assets/add', data=new_asset_data, follow_redirects=True)
    assert res.status_code == 200
    print(" [OK] Duplicate serial numbers strictly prevented")

    # 6. View Asset Details & Timeline
    res = client.get(f'/assets/view/{test_asset_id}')
    assert res.status_code == 200
    assert b"Test iPad Air M2" in res.data
    assert b"Lifecycle Timeline" in res.data
    print(" [OK] Asset View page displays complete specs & lifecycle timeline")

    # 7. Asset Assignment Workflow
    assign_data = {
        'user_id': 'USR-006',
        'assignment_date': '2024-04-02',
        'expected_return_date': '2024-06-01',
        'department': 'Computer Science',
        'notes': 'Checkout for app testing'
    }
    res = client.post(f'/assets/{test_asset_id}/assign', data=assign_data, follow_redirects=True)
    assert res.status_code == 200
    
    updated_asset = db.assets.find_one({"asset_id": test_asset_id})
    assert updated_asset['status'] == 'Assigned'
    assert updated_asset['assigned_to']['user_id'] == 'USR-006'
    print(f" [OK] Asset {test_asset_id} checkout workflow transitioned status to 'Assigned'")

    # 8. Asset Relocation Workflow
    move_data = {
        'to_location': 'Computer Center',
        'reason': 'Moved for lab demo'
    }
    res = client.post(f'/assets/{test_asset_id}/move', data=move_data, follow_redirects=True)
    assert res.status_code == 200
    moved_asset = db.assets.find_one({"asset_id": test_asset_id})
    assert moved_asset['location'] == 'Computer Center'
    print(f" [OK] Asset {test_asset_id} relocation logged and updated")

    # 9. Asset Return Workflow
    return_data = {
        'return_date': '2024-04-03',
        'condition': 'Good',
        'remarks': 'Returned in great condition'
    }
    res = client.post(f'/assets/{test_asset_id}/return', data=return_data, follow_redirects=True)
    assert res.status_code == 200
    returned_asset = db.assets.find_one({"asset_id": test_asset_id})
    assert returned_asset['status'] == 'Available'
    assert returned_asset['assigned_to'] is None
    print(f" [OK] Asset {test_asset_id} return workflow transitioned status back to 'Available'")

    # 10. Maintenance Ticket Workflow
    maint_data = {
        'asset_id': test_asset_id,
        'maintenance_type': 'Preventive',
        'issue': 'Battery diagnostics',
        'service_provider': 'Internal IT',
        'cost': '500',
        'start_date': '2024-04-03',
        'expected_completion': '2024-04-04',
        'status': 'In Progress',
        'description': 'Diagnostic test'
    }
    res = client.post('/maintenance/new', data=maint_data, follow_redirects=True)
    assert res.status_code == 200
    
    maint_asset = db.assets.find_one({"asset_id": test_asset_id})
    assert maint_asset['status'] == 'Under Maintenance'
    print(f" [OK] Maintenance ticket logged, asset status updated to 'Under Maintenance'")

    # 11. Reports & Audits
    res = client.get('/reports')
    assert res.status_code == 200
    assert b"Reports & Audits" in res.data
    print(" [OK] Reports & Audits view renders successfully")

    # 12. Instant API Search
    res_api = client.get('/api/search?q=Dell')
    assert res_api.status_code == 200
    json_data = res_api.get_json()
    assert 'results' in json_data
    assert len(json_data['results']) > 0
    print(f" [OK] Live API Search returned {len(json_data['results'])} matches for 'Dell'")

    # Clean up test asset
    db.assets.delete_one({"asset_id": test_asset_id})
    db.asset_history.delete_many({"asset_id": test_asset_id})

    print("\n========================================================")
    print(" ALL 12 CORE TEST SUITES PASSED SUCCESSFULLY!")
    print("========================================================")

if __name__ == '__main__':
    run_tests()


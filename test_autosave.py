#!/usr/bin/env python
"""
Test script for auto-save functionality
Run this script to test the draft endpoints
"""

import os
import sys
import django
import json
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_config.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from core.models.contact import Contact
from core.models.Documents import MainReceiptDocument, ReceiptDocument
from core.models.DraftReceipt import DraftReceipt

def create_test_data():
    """Create test data for testing"""
    print("🔧 Creating test data...")
    
    # Create test company
    company, created = Contact.objects.get_or_create(
        tin_number="1234567890",
        defaults={
            "name": "Test Company",
            "address": "Test Address"
        }
    )
    print(f"✅ Company: {company.name} (TIN: {company.tin_number})")
    
    # Create test uploaded document
    main_receipt, created = MainReceiptDocument.objects.get_or_create(
        receipt_number="246",
        defaults={
            "receipt_date": datetime.now().date(),
            "main_receipt_filename": "test.pdf",
            "main_receipt_content_type": "application/pdf"
        }
    )
    print(f"✅ Main Receipt: {main_receipt.receipt_number}")
    
    # Create ReceiptDocument
    receipt_doc, created = ReceiptDocument.objects.get_or_create(
        main_receipt=main_receipt,
        for_company=company,
        defaults={
            "status": "uploaded"
        }
    )
    print(f"✅ Receipt Document: {receipt_doc.id} (Status: {receipt_doc.status})")
    
    return company, main_receipt, receipt_doc

def test_draft_endpoints():
    """Test the draft endpoints"""
    print("\n🧪 Testing Draft Endpoints...")
    
    # Create test data
    company, main_receipt, receipt_doc = create_test_data()
    
    # Create test client
    client = Client()
    
    # Simulate authentication by setting company_tin
    client.defaults['HTTP_X_COMPANY_TIN'] = company.tin_number
    
    # Test 1: GET draft (should create new draft)
    print("\n📝 Test 1: GET /api/drafts/?receipt_number=FS246")
    response = client.get('/api/drafts/', {'receipt_number': 'FS246'})
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Draft created/loaded:")
        print(f"   - Draft ID: {data['draft_id']}")
        print(f"   - Uploaded Doc: {data['uploaded_document_number']}")
        print(f"   - Revision: {data['revision']}")
        print(f"   - Status: {data['status']}")
        
        draft_id = data['draft_id']
        current_revision = data['revision']
    else:
        print(f"❌ Failed to get draft: {response.content}")
        return
    
    # Test 2: PATCH draft (auto-save)
    print("\n💾 Test 2: PATCH /api/drafts/ (Auto-save)")
    draft_data = {
        "receipt_number": "FS246",
        "expected_revision": current_revision,
        "data": {
            "receipt_number": "FS246",
            "receipt_date": "2024-01-15",
            "calendar_type": "gregorian",
            "receipt_category_id": 1,
            "receipt_kind_id": 1,
            "receipt_type_id": 1,
            "receipt_name_id": 1,
            "issued_by_details": {
                "name": "Test Supplier",
                "tin_number": "0987654321",
                "address": "Supplier Address"
            },
            "issued_to_details": {
                "name": "Test Buyer",
                "tin_number": "1234567890",
                "address": "Buyer Address"
            },
            "payment_method_type": "cash",
            "bank_name": "",
            "machine_number": "",
            "is_withholding_applicable": False,
            "items": [
                {
                    "item_description": "Test Item 1",
                    "quantity": 2,
                    "unit_cost": 100.00
                },
                {
                    "item_description": "Test Item 2",
                    "quantity": 1,
                    "unit_cost": 50.00
                }
            ]
        }
    }
    
    response = client.patch(
        '/api/drafts/',
        data=json.dumps(draft_data),
        content_type='application/json'
    )
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Draft saved successfully:")
        print(f"   - New Revision: {data['revision']}")
        current_revision = data['revision']
    else:
        print(f"❌ Failed to save draft: {response.content}")
        return
    
    # Test 3: GET draft again (should return saved data)
    print("\n📖 Test 3: GET /api/drafts/?receipt_number=FS246 (Load saved data)")
    response = client.get('/api/drafts/', {'receipt_number': 'FS246'})
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Draft loaded with saved data:")
        print(f"   - Revision: {data['revision']}")
        print(f"   - Items count: {len(data['data'].get('items', []))}")
        print(f"   - Issued by: {data['data'].get('issued_by_details', {}).get('name')}")
    else:
        print(f"❌ Failed to load draft: {response.content}")
    
    # Test 4: Conflict detection
    print("\n⚠️ Test 4: Conflict Detection (Wrong revision)")
    conflict_data = {
        "receipt_number": "FS246",
        "expected_revision": current_revision - 1,  # Wrong revision
        "data": {
            "receipt_number": "FS246",
            "items": [{"item_description": "Conflict Item"}]
        }
    }
    
    response = client.patch(
        '/api/drafts/',
        data=json.dumps(conflict_data),
        content_type='application/json'
    )
    print(f"Status: {response.status_code}")
    
    if response.status_code == 409:
        data = response.json()
        print(f"✅ Conflict detected correctly:")
        print(f"   - Error: {data['error']}")
        print(f"   - Current revision: {data['current']['revision']}")
    else:
        print(f"❌ Conflict detection failed: {response.content}")
    
    # Test 5: Database verification
    print("\n🔍 Test 5: Database Verification")
    try:
        draft = DraftReceipt.objects.get(id=draft_id)
        print(f"✅ Draft found in database:")
        print(f"   - ID: {draft.id}")
        print(f"   - Company: {draft.company.name}")
        print(f"   - Uploaded Doc: {draft.uploaded_document_number}")
        print(f"   - Receipt Number: {draft.receipt_number}")
        print(f"   - Revision: {draft.revision}")
        print(f"   - Status: {draft.status}")
        print(f"   - Created: {draft.created_at}")
        print(f"   - Updated: {draft.updated_at}")
        
        # Check data content
        data = draft.data
        print(f"   - Items in data: {len(data.get('items', []))}")
        print(f"   - Issued by: {data.get('issued_by_details', {}).get('name')}")
        
    except DraftReceipt.DoesNotExist:
        print("❌ Draft not found in database")
    
    print("\n🎉 Auto-save testing completed!")

def test_draft_serializer():
    """Test the DraftDataSerializer"""
    print("\n🧪 Testing DraftDataSerializer...")
    
    from core.serializers.DraftDataSerializer import DraftDataSerializer
    
    # Test valid data
    valid_data = {
        "receipt_number": "FS246",
        "receipt_date": "2024-01-15",
        "calendar_type": "gregorian",
        "receipt_category_id": 1,
        "receipt_kind_id": 1,
        "receipt_type_id": 1,
        "receipt_name_id": 1,
        "issued_by_details": {
            "name": "Test Supplier",
            "tin_number": "0987654321",
            "address": "Supplier Address"
        },
        "issued_to_details": {
            "name": "Test Buyer",
            "tin_number": "1234567890",
            "address": "Buyer Address"
        },
        "payment_method_type": "cash",
        "items": [
            {
                "item_description": "Test Item",
                "quantity": 1,
                "unit_cost": 100.00
            }
        ]
    }
    
    serializer = DraftDataSerializer(data=valid_data)
    if serializer.is_valid():
        print("✅ DraftDataSerializer validation passed")
        print(f"   - Validated data: {len(serializer.validated_data)} fields")
    else:
        print("❌ DraftDataSerializer validation failed:")
        print(f"   - Errors: {serializer.errors}")

def cleanup_test_data():
    """Clean up test data"""
    print("\n🧹 Cleaning up test data...")
    
    # Delete test drafts
    DraftReceipt.objects.filter(uploaded_document_number="246").delete()
    print("✅ Test drafts deleted")
    
    # Delete test documents
    ReceiptDocument.objects.filter(main_receipt__receipt_number="246").delete()
    MainReceiptDocument.objects.filter(receipt_number="246").delete()
    print("✅ Test documents deleted")

if __name__ == "__main__":
    print("🚀 Starting Auto-save Backend Testing...")
    
    try:
        # Test serializer
        test_draft_serializer()
        
        # Test endpoints
        test_draft_endpoints()
        
        # Cleanup
        cleanup_test_data()
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

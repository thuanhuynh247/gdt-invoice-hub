"""
Tests for AI Expense Classifier feature (US-029).
Covers database schema updates, AI classification engine few-shot mapping, keyword fallback routines, and REST API routes.
"""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock
import pytest

from extensions import db
from invoices.models import Invoice, LineItem
from invoices.ai_service import AIExpenseClassifier
from invoices.scheduler import save_scheduler_settings


@pytest.fixture
def sample_invoice(app):
    """Seed a sample invoice and items in the database for testing."""
    with app.app_context():
        LineItem.query.delete()
        Invoice.query.delete()
        db.session.commit()

        invoice = Invoice(
            id="INV-AI-TEST-999",
            number="99999",
            date="2026-05-23",
            seller_name="Cong ty TNHH Van Phong Pham B",
            seller_mst="0101234567",
            seller_address="Ha Noi",
            buyer_name="Cong ty TNHH Giai Phap Cong Nghe",
            buyer_mst="0309876543",
            buyer_address="TP HCM",
            amount_before_tax=100000.0,
            tax_amount=10000.0,
            total_amount=110000.0,
            has_signature=True,
            signing_date="2026-05-23",
            payment_method="TM/CK",
            imported_at="2026-05-23 10:00:00",
            import_status="imported"
        )
        db.session.add(invoice)

        item1 = LineItem(
            id=9991,
            invoice_id="INV-AI-TEST-999",
            item_name="Giấy in Double A A4 70gsm",
            quantity=2,
            unit_price=50000.0,
            amount_before_tax=100000.0,
            tax_rate="10%",
            tax_amount=10000.0
        )
        item2 = LineItem(
            id=9992,
            invoice_id="INV-AI-TEST-999",
            item_name="Chuột không dây Logitech M331",
            quantity=1,
            unit_price=300000.0,
            amount_before_tax=300000.0,
            tax_rate="10%",
            tax_amount=30000.0
        )
        db.session.add(item1)
        db.session.add(item2)
        db.session.commit()
        
        yield invoice


def test_expense_classifier_fallback_keywords():
    """Verify that the semantic keyword classification covers all standard groups."""
    classifier = AIExpenseClassifier()
    
    # Test cases mapping item descriptions to canonical groups
    test_cases = [
        ("Giấy in Double A A4 80gsm", "Văn phòng phẩm & Thiết bị văn phòng"),
        ("Bút bi Thiên Long", "Văn phòng phẩm & Thiết bị văn phòng"),
        ("Laptop Asus ROG", "Thiết bị công nghệ & Phần mềm"),
        ("Bàn phím cơ Keychron", "Thiết bị công nghệ & Phần mềm"),
        ("Ăn trưa tiếp đối tác công ty A", "Chi phí tiếp khách & Hội nghị"),
        ("Coffee meeting", "Chi phí tiếp khách & Hội nghị"),
        ("Quảng cáo Google Search", "Quảng cáo, Tiếp thị & Sự kiện"),
        ("Banner triển lãm hội chợ", "Quảng cáo, Tiếp thị & Sự kiện"),
        ("Phí vận chuyển bưu điện", "Vận chuyển, Giao hàng & Logistics"),
        ("Grab giao hàng hỏa tốc", "Vận chuyển, Giao hàng & Logistics"),
        ("Hóa đơn tiền điện tháng 5", "Chi phí dịch vụ công cộng & Tiện ích"),
        ("Cước thuê bao internet FPT", "Chi phí dịch vụ công cộng & Tiện ích"),
        ("Sửa chữa điều hòa văn phòng", "Sửa chữa, Bảo trì & Nâng cấp"),
        ("Bảo dưỡng xe máy xúc", "Sửa chữa, Bảo trì & Nâng cấp"),
        ("Vật tư linh tinh pantry", "Chi phí khác & Vật tư dùng chung")
    ]
    
    for desc, expected_cat in test_cases:
        assert classifier.classify_item_fallback(desc) == expected_cat


def test_expense_classifier_database_attributes(app, sample_invoice):
    """Verify database schema persistence for the line items category column."""
    with app.app_context():
        item = db.session.get(LineItem, 9991)
        assert item.expense_category is None
        assert item.to_dict()["expense_category"] == "Chưa phân loại"
        
        # Test manual update and serialization
        item.expense_category = "Thiết bị công nghệ & Phần mềm"
        db.session.commit()
        
        updated_item = db.session.get(LineItem, 9991)
        assert updated_item.expense_category == "Thiết bị công nghệ & Phần mềm"
        assert updated_item.to_dict()["expense_category"] == "Thiết bị công nghệ & Phần mềm"


def test_api_classify_invoice_items(logged_in_client, sample_invoice):
    """Verify that client REST API correctly requests classification and saves state."""
    # Make post request to classify items
    resp = logged_in_client.post("/api/ai/classify-items", json={"invoice_id": "INV-AI-TEST-999"})
    assert resp.status_code == 200
    
    data = resp.get_json()
    assert data["success"] is True
    assert len(data["classified_items"]) == 2
    
    # Assert database records were updated
    resp_details = logged_in_client.get("/api/invoices/INV-AI-TEST-999/details")
    assert resp_details.status_code == 200
    details = resp_details.get_json()
    
    categories = [it["expense_category"] for it in details["line_items"]]
    assert "Văn phòng phẩm & Thiết bị văn phòng" in categories
    assert "Thiết bị công nghệ & Phần mềm" in categories


def test_api_update_item_category(logged_in_client, sample_invoice):
    """Verify that manual overrides of categories successfully update database and serialize."""
    # Update item 9991 from office to shipping
    payload = {
        "item_id": 9991,
        "category": "Vận chuyển, Giao hàng & Logistics"
    }
    resp = logged_in_client.post("/api/ai/update-item-category", json=payload)
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True
    
    # Verify the details are updated
    resp_details = logged_in_client.get("/api/invoices/INV-AI-TEST-999/details")
    details = resp_details.get_json()
    
    target_item = next(it for it in details["line_items"] if it["id"] == 9991)
    assert target_item["expense_category"] == "Vận chuyển, Giao hàng & Logistics"


def test_api_update_item_category_invalid(logged_in_client, sample_invoice):
    """Verify error responses for invalid inputs on the update route."""
    # Invalid category
    payload = {
        "item_id": 9991,
        "category": "Nhom chi phi linh tinh ko ton tai"
    }
    resp = logged_in_client.post("/api/ai/update-item-category", json=payload)
    assert resp.status_code == 400
    assert "Danh mục chi phí không hợp lệ" in resp.get_json()["error"]

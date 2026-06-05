"""Tests for Version 26.0.0 Advanced Compliance & Tax Advisory features (US-380 to US-385)."""

from __future__ import annotations

import json
from datetime import datetime
import pytest

from invoices.v26_service import (
    calculate_statutory_insurance,
    audit_social_insurance,
    export_si_reconciliation_csv,
    reconcile_tax_ledger,
    generate_napas_vietqr_payload,
    TaxLawKnowledgeGraph,
    compose_audit_defense_letter
)


def test_statutory_insurance_calculation():
    """US-380: Test statutory social insurance contribution rates and cap limits."""
    basic_salary = 2340000.0  # VND
    cap_wage = basic_salary * 20  # 46,800,000 VND

    # 1. Below cap gross salary (15,000,000 VND)
    res_below = calculate_statutory_insurance(15000000.0, basic_salary)
    assert res_below["si_hi_base"] == 15000000.0
    assert not res_below["is_capped"]
    assert res_below["employee"]["BHXH"] == 15000000.0 * 0.08
    assert res_below["employee"]["BHYT"] == 15000000.0 * 0.015
    assert res_below["employee"]["BHTN"] == 15000000.0 * 0.01
    assert res_below["total_employee"] == 15000000.0 * 0.105
    assert res_below["total_employer"] == 15000000.0 * 0.215

    # 2. Above cap gross salary (60,000,000 VND)
    res_above = calculate_statutory_insurance(60000000.0, basic_salary)
    assert res_above["si_hi_base"] == cap_wage
    assert res_above["is_capped"]
    assert res_above["total_employee"] == cap_wage * 0.105
    assert res_above["total_employer"] == cap_wage * 0.215


def test_payroll_audit_reconciliation():
    """US-380 & US-381: Test social insurance payroll audit matching and CSV exporter."""
    basic_salary = 2340000.0
    
    mock_payroll = [
        {"id": "EMP-001", "name": "Nguyễn Văn A", "gross_salary": 15000000.0, "withheld_insurance": 1575000.0},  # Match
        {"id": "EMP-002", "name": "Trần Thị B", "gross_salary": 25000000.0, "withheld_insurance": 2300000.0},  # Mismatch (calculated is 2,625,000)
    ]
    
    audit_res = audit_social_insurance(mock_payroll, basic_salary)
    assert audit_res["status"] == "flagged"
    assert audit_res["compliance_score"] == 50
    assert len(audit_res["discrepancies"]) == 1
    assert audit_res["discrepancies"][0]["employee_id"] == "EMP-002"
    
    # Test CSV export
    csv_report = export_si_reconciliation_csv(audit_res)
    assert "BÁO CÁO ĐỐI CHIẾU TRÍCH ĐÓNG BẢO HIỂM XÃ HỘI" in csv_report
    assert "Nguyễn Văn A" in csv_report
    assert "Trần Thị B" in csv_report
    assert "FLAGGED" in csv_report


def test_tax_ledger_sync_reconciliation():
    """US-382: Test GDT e-Tax ledger sync and accounting book reconciliation."""
    local_payments = [
        {"tax_type": "VAT", "amount": 80000000.0},
        {"tax_type": "CIT", "amount": 120000000.0},
        {"tax_type": "PIT", "amount": 10000000.0}  # Underpaid vs eTax paid 12,000,000
    ]
    
    mst = "0109999999"
    reconciled = reconcile_tax_ledger(mst, local_payments)
    
    assert reconciled["status"] == "flagged"
    assert len(reconciled["discrepancies"]) == 1
    mismatches = [d["tax_type"] for d in reconciled["discrepancies"]]
    assert "PIT" in mismatches


def test_vietqr_dynamic_slip_napas():
    """US-383: Test dynamic VietQR EMVCo tag generation and napas string integrity."""
    mst = "0109999999"
    amount = 5000000.0
    tax_type = "CIT"
    
    qr_payload = generate_napas_vietqr_payload(tax_type, amount, mst)
    
    assert qr_payload["status"] == "pending"
    assert qr_payload["amount"] == amount
    assert qr_payload["beneficiary"] == "KHO BAC NHA NUOC"
    assert "000201" in qr_payload["vietqr_string"]  # EMVCo version tag
    assert qr_payload["vietqr_string"].endswith(qr_payload["vietqr_string"][-4:])  # Ends with checksum


def test_tax_knowledge_graph_traversal():
    """US-384: Test local tax law knowledge graph construction and lookup search."""
    kg = TaxLawKnowledgeGraph()
    
    # Keyword search for signing time
    res = kg.keyword_search("ký số")
    assert len(res) > 0
    assert any("Decree 123" in doc["document"] for doc in res)
    
    # Query citations
    citations = kg.get_related_citations("D123-A15")
    assert len(citations) > 0
    assert citations[0]["id"] == "C80-A8"


def test_audit_defense_letter_composer():
    """US-385: Test AI audit defense composer letter formatting and legal quotations."""
    profile = {
        "mst": "0109999999",
        "company_name": "Công ty TNHH Ánh Sáng",
        "district": "Cục Thuế Hà Nội",
        "representative": "Nguyễn Văn Giám Đốc"
    }
    
    # Test related party EBITDA warning
    context = {
        "ebitda_amount": 10000000000.0,
        "net_interest_expense": 4000000000.0
    }
    
    letter = compose_audit_defense_letter(profile, "RELATED_PARTY_EBITDA", context)
    assert "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" in letter
    assert "Công ty TNHH Ánh Sáng" in letter
    assert "30%" in letter
    assert "EBITDA" in letter
    assert "Decree 132/2020" in letter


def test_v26_endpoints(logged_in_client):
    """US-381, US-383, US-385: Test routes HTTP response and authentication gates."""
    # 1. Test page load
    resp = logged_in_client.get("/v26-compliance")
    assert resp.status_code == 200
    
    # 2. Test payroll audit API
    resp = logged_in_client.post("/api/compliance/insurance-audit?basic_salary=2340000")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["compliance_score"] < 100
    
    # 3. Test export CSV
    resp = logged_in_client.get("/api/compliance/insurance-export-csv?basic_salary=2340000")
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    assert b"Nguy\xe1\xbb\x85n V\xc4\x83n A" in resp.data or b"Nguyen Van A" in resp.data
    
    # 4. Test ledger reconciliation
    resp = logged_in_client.post(
        "/api/compliance/tax-ledger-reconcile",
        json={"local_payments": [{"tax_type": "VAT", "amount": 80000000.0}]}
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    
    # 5. Test VietQR generation and simulation
    resp = logged_in_client.post(
        "/api/compliance/vietqr-generate",
        json={"tax_type": "VAT", "amount": 2500000}
    )
    assert resp.status_code == 200
    data = resp.get_json()
    tx_id = data["transaction_id"]
    
    resp = logged_in_client.post(
        "/api/compliance/vietqr-confirm",
        json={"transaction_id": tx_id}
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "paid"
    
    # 6. Test law KG query
    resp = logged_in_client.get("/api/compliance/kg-query?query=chuyển khoản")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["results"]) > 0
    
    # 7. Test defense composer
    resp = logged_in_client.post(
        "/api/compliance/defense-compose",
        json={
            "warning_type": "LATE_SIGNING",
            "context": {"declaration_period": "Tháng 03/2026"}
        }
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "letter_html" in data
    assert "DF-" in data["letter_html"]

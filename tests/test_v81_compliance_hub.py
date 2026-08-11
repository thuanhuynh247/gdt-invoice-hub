"""Comprehensive Test Suite for V81 PIT Compliance Hub & Form 08/CK-TNCN Engine."""

import os
import shutil
import pytest
from invoices.v81_service import V81PITComplianceService
from invoices.telemetry_stream import TelemetryEventBus, telemetry_bus


@pytest.fixture
def test_data_dir(tmp_path):
    """Provide an isolated temporary data directory for V81 tests."""
    data_dir = tmp_path / "v81_test_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    yield str(data_dir)
    shutil.rmtree(str(data_dir), ignore_errors=True)


def test_v81_service_db_initialization(test_data_dir):
    """Test that V81 service creates isolated database and schema."""
    service = V81PITComplianceService(test_data_dir)
    mst = "0109988776"
    conn = service._get_db_connection(mst)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='v81_pit_audit_logs'")
    row = cursor.fetchone()
    conn.close()
    assert row is not None


def test_v81_freelance_under_2m_no_withholding(test_data_dir):
    """Payments under 2,000,000 VND to freelancers are exempt from 10% withholding."""
    service = V81PITComplianceService(test_data_dir)
    mst = "0109988776"
    res = service.audit_pit_transaction(
        mst=mst,
        person_name="Nguyễn Văn A",
        payment_amount=1_800_000.0,
        personal_id_or_mst="8000000001",
        contract_type="freelance",
        has_form_08=False
    )
    assert res["withholding_tax"] == 0.0
    assert res["applicable_tax_rate"] == 0.0
    assert res["risk_level"] == "SAFE"
    assert res["compliance_score"] == 100.0


def test_v81_freelance_above_2m_no_form08_withholding_10pct(test_data_dir):
    """Payments >= 2M to freelancers without Form 08 require 10% withholding."""
    service = V81PITComplianceService(test_data_dir)
    mst = "0109988776"
    res = service.audit_pit_transaction(
        mst=mst,
        person_name="Trần Văn B",
        payment_amount=10_000_000.0,
        personal_id_or_mst="8000000002",
        contract_type="freelance",
        has_form_08=False,
        has_elec_cert=True,
        cert_number="CT-2026-0001"
    )
    assert res["withholding_tax"] == 1_000_000.0
    assert res["applicable_tax_rate"] == 10.0
    assert res["risk_level"] == "SAFE"
    assert res["compliance_score"] == 100.0


def test_v81_freelance_valid_form08_exempt(test_data_dir):
    """Valid Form 08 (MST registered, estimated income <= 132M, sole source) temporarily exempts 10%."""
    service = V81PITComplianceService(test_data_dir)
    mst = "0109988776"
    res = service.audit_pit_transaction(
        mst=mst,
        person_name="Lê Văn Hùng",
        payment_amount=15_000_000.0,
        personal_id_or_mst="8012345678",
        contract_type="freelance",
        has_form_08=True,
        estimated_annual_income=90_000_000.0,
        is_sole_income_source=True
    )
    assert res["withholding_tax"] == 0.0
    assert res["applicable_tax_rate"] == 0.0
    assert res["form_08_status"] == "VALID"
    assert res["risk_level"] == "SAFE"
    assert res["compliance_score"] == 100.0


def test_v81_freelance_form08_missing_mst_violation(test_data_dir):
    """Form 08 without registered MST is legally void under TT 111/2013 -> 10% withholding & critical risk."""
    service = V81PITComplianceService(test_data_dir)
    mst = "0109988776"
    res = service.audit_pit_transaction(
        mst=mst,
        person_name="Trần Thị Mai",
        payment_amount=8_000_000.0,
        personal_id_or_mst="",  # Missing MST
        contract_type="freelance",
        has_form_08=True,
        estimated_annual_income=50_000_000.0,
        is_sole_income_source=True
    )
    assert res["withholding_tax"] == 800_000.0
    assert res["applicable_tax_rate"] == 10.0
    assert res["form_08_status"] == "INVALID"
    assert res["risk_level"] == "CRITICAL"
    assert any("MST cá nhân" in v for v in res["violations"])


def test_v81_freelance_form08_excess_income_violation(test_data_dir):
    """Form 08 with estimated annual income > 132M is invalid -> 10% withholding."""
    service = V81PITComplianceService(test_data_dir)
    mst = "0109988776"
    res = service.audit_pit_transaction(
        mst=mst,
        person_name="Phạm Văn D",
        payment_amount=20_000_000.0,
        personal_id_or_mst="8000000004",
        contract_type="freelance",
        has_form_08=True,
        estimated_annual_income=150_000_000.0,  # > 132M
        is_sole_income_source=True
    )
    assert res["withholding_tax"] == 2_000_000.0
    assert res["form_08_status"] == "INVALID"
    assert any("132,000,000" in v for v in res["violations"])


def test_v81_resident_contract_progressive_calculation(test_data_dir):
    """Labor contract >= 3 months uses progressive tariff (Biểu thuế lũy tiến từng phần)."""
    service = V81PITComplianceService(test_data_dir)
    mst = "0109988776"
    # Gross: 30M, Personal relief: 11M, Dependents: 1 (4.4M), Insurance: 3M -> Taxable: 30 - 11 - 4.4 - 3 = 11.6M
    # Tax: 5M * 5% (250k) + 5M * 10% (500k) + 1.6M * 15% (240k) = 990k VND
    res = service.audit_pit_transaction(
        mst=mst,
        person_name="Hoàng Văn E",
        payment_amount=30_000_000.0,
        personal_id_or_mst="8000000005",
        contract_type="resident_contract",
        num_dependents=1,
        insurance_deduction=3_000_000.0
    )
    assert res["taxable_income"] == 11_600_000.0
    assert res["withholding_tax"] == 990_000.0
    assert res["risk_level"] == "SAFE"


def test_v81_non_resident_20pct_withholding(test_data_dir):
    """Non-resident individuals must have flat 20% tax withheld on total gross."""
    service = V81PITComplianceService(test_data_dir)
    mst = "0109988776"
    res = service.audit_pit_transaction(
        mst=mst,
        person_name="John Smith (Chuyên gia nước ngoài)",
        payment_amount=50_000_000.0,
        personal_id_or_mst="PASSPORT-US99",
        contract_type="non_resident",
        has_elec_cert=True,
        cert_number="CT-2026-NR01"
    )
    assert res["withholding_tax"] == 10_000_000.0
    assert res["applicable_tax_rate"] == 20.0
    assert res["risk_level"] == "SAFE"


def test_v81_form_05kk_xml_generation(test_data_dir):
    """Test generating Form 05/KK-TNCN XML document."""
    service = V81PITComplianceService(test_data_dir)
    mst = "0109988776"
    # Insert 2 transactions
    service.audit_pit_transaction(mst=mst, person_name="A", payment_amount=10_000_000.0, contract_type="freelance")
    service.audit_pit_transaction(mst=mst, person_name="B", payment_amount=20_000_000.0, contract_type="resident_contract")

    xml = service.generate_05kk_xml(mst, "Q1/2026", "CONG TY TNHH TEST")
    assert "<?xml" in xml
    assert "<HSoThueDTu" in xml
    assert "<TKhai>05/KK-TNCN</TKhai>" in xml
    assert f"<MST>{mst}</MST>" in xml
    assert "<CT27>30000000</CT27>" in xml


def test_v81_delete_log_and_history(test_data_dir):
    """Test deleting an audit log and querying history."""
    service = V81PITComplianceService(test_data_dir)
    mst = "0109988776"
    res = service.audit_pit_transaction(mst=mst, person_name="Test Person", payment_amount=5_000_000.0)
    history = service.get_history(mst)
    assert len(history) >= 1
    log_id = history[0]["id"]

    del_success = service.delete_log(mst, log_id)
    assert del_success is True
    history_after = service.get_history(mst)
    assert not any(h["id"] == log_id for h in history_after)


def test_telemetry_event_bus():
    """Test SSE Telemetry event bus publishing and subscriber queue."""
    bus = TelemetryEventBus()
    q = bus.subscribe()
    
    event = bus.publish(
        event_type="TEST_EVENT",
        message="Testing telemetry bus integration.",
        level="SUCCESS",
        source="TEST_SUITE"
    )
    assert event["type"] == "TEST_EVENT"
    
    received = q.get(timeout=1.0)
    assert received["type"] == "TEST_EVENT"
    assert received["message"] == "Testing telemetry bus integration."
    bus.unsubscribe(q)

"""Unit and integration tests for Bank Feed Ingestion & Invoice Matching (US-322, US-323)."""

from __future__ import annotations

import pytest
from extensions import db
from invoices.models import Invoice, Partner, BankTransaction
from invoices.bank_stream_service import BankStreamService


def test_bank_feed_ingestion_csv(app):
    """Test parsing and ingesting custom Vietcombank CSV statements."""
    with app.app_context():
        # Clear existing transactions
        BankTransaction.query.delete()
        db.session.commit()

        # CSV row layout: Date, TxID, Amount, CreditDebit, PartnerAccount, PartnerName, RefCode
        csv_data = (
            "2026-06-01,TXN9901,15000000.0,CRDT,110229384,CONG TY TNHH ABC,Thanh toan hoa don 10234\n"
            "2026-06-02,TXN9902,25000000.0,DBIT,110229385,CONG TY TNHH XYZ,Mua thiet bi van phong hoa don 10235\n"
        )

        service = BankStreamService()
        inserted = service.ingest_bank_statement(csv_data, "0101234567", "Vietcombank", "csv")
        assert inserted == 2

        # Verify database storage
        txs = BankTransaction.query.filter_by(taxpayer_mst="0101234567").all()
        assert len(txs) == 2
        assert txs[0].id == "TXN9901"
        assert txs[0].amount == 15000000.0
        assert txs[1].id == "TXN9902"
        assert txs[1].amount == -25000000.0  # Debit becomes negative


def test_bank_feed_ingestion_iso20022_xml(app):
    """Test parsing and ingesting ISO 20022 standard XML statements."""
    with app.app_context():
        BankTransaction.query.delete()
        db.session.commit()

        xml_data = """<?xml version="1.0" encoding="UTF-8"?>
        <Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.02">
            <BkToCstmrStmt>
                <Stmt>
                    <Ntry>
                        <Amt Ccy="VND">42000000.00</Amt>
                        <CdtDbtInd>CRDT</CdtDbtInd>
                        <BookgDt>
                            <Dt>2026-06-03</Dt>
                        </BookgDt>
                        <AcctSvcrRef>ISO_TXN_001</AcctSvcrRef>
                        <NtryDtls>
                            <TxDtls>
                                <RltdPties>
                                    <Dbtr>
                                        <Nm>CONG TY CỔ PHẦN ALPHA</Nm>
                                    </Dbtr>
                                    <DbtrAcct>
                                        <Id>
                                            <Othr>
                                                <Id>999888777666</Id>
                                            </Othr>
                                        </Id>
                                    </DbtrAcct>
                                </RltdPties>
                                <RmtInf>
                                    <Ustrd>Thanh toan hop dong alpha, hoa don 501</Ustrd>
                                </RmtInf>
                            </TxDtls>
                        </NtryDtls>
                    </Ntry>
                </Stmt>
            </BkToCstmrStmt>
        </Document>
        """

        service = BankStreamService()
        inserted = service.ingest_bank_statement(xml_data, "0101234567", "Techcombank", "xml")
        assert inserted == 1

        tx = BankTransaction.query.filter_by(id="ISO_TXN_001").first()
        assert tx is not None
        assert tx.amount == 42000000.0
        assert "CONG TY CỔ PHẦN ALPHA" in tx.description


def test_bank_to_invoice_matcher(app):
    """Test pairing transactions against invoices (exact, partial, and no-match >= 20M warning)."""
    with app.app_context():
        # Setup mock invoices & partners
        Invoice.query.delete()
        Partner.query.delete()
        BankTransaction.query.delete()
        db.session.commit()

        # Add invoice 101 (Exact Match candidate)
        inv_exact = Invoice(
            id="101",
            taxpayer_mst="0101234567",
            number="101",
            seller_mst="0202020202",
            seller_name="CONG TY TNHH MISA",
            total_amount=15000000.0,
            date="2026-06-01",
            imported_at="2026-06-01T00:00:00Z"
        )
        # Add invoice 102 (Partial Match candidate due to amount difference)
        inv_partial = Invoice(
            id="102",
            taxpayer_mst="0101234567",
            number="102",
            seller_mst="0303030303",
            seller_name="CONG TY TNHH ODOO",
            total_amount=25000000.0,
            date="2026-06-02",
            imported_at="2026-06-02T00:00:00Z"
        )
        db.session.add(inv_exact)
        db.session.add(inv_partial)

        # Add partners
        partner_misa = Partner(name="CONG TY TNHH MISA", mst="0202020202")
        partner_odoo = Partner(name="CONG TY TNHH ODOO", mst="0303030303")
        db.session.add(partner_misa)
        db.session.add(partner_odoo)

        # Add transactions to match
        tx1 = BankTransaction(
            id="TX_MATCH_01",
            taxpayer_mst="0101234567",
            bank_name="Vietcombank",
            transaction_date="2026-06-03",
            amount=15000000.0,
            description="Thanh toan hoa don 101 | Đối tác: CONG TY TNHH MISA",
            status="unreconciled",
            imported_at="2026-06-03T12:00:00Z"
        )
        tx2 = BankTransaction(
            id="TX_MATCH_02",
            taxpayer_mst="0101234567",
            bank_name="Vietcombank",
            transaction_date="2026-06-03",
            amount=24500000.0,  # Mismatch amount: 24.5M vs 25M
            description="Thanh toan hoa don 102 | Đối tác: CONG TY TNHH ODOO",
            status="unreconciled",
            imported_at="2026-06-03T12:00:00Z"
        )
        tx3 = BankTransaction(
            id="TX_MATCH_03",
            taxpayer_mst="0101234567",
            bank_name="Vietcombank",
            transaction_date="2026-06-03",
            amount=30000000.0,  # Value >= 20M without match
            description="Thanh toan chi phi hop dong khong ro nguon goc",
            status="unreconciled",
            imported_at="2026-06-03T12:00:00Z"
        )
        db.session.add(tx1)
        db.session.add(tx2)
        db.session.add(tx3)
        db.session.commit()

        service = BankStreamService()
        result = service.execute_transaction_matching("0101234567")

        assert result["success"] is True
        assert result["matched_count"] == 2
        assert result["warnings_raised"] == 2  # tx2 (amount mismatch) + tx3 (unmatched >= 20M warning)

        # Verify match status
        res_tx1 = BankTransaction.query.filter_by(id="TX_MATCH_01").first()
        assert res_tx1.status == "matched"
        assert res_tx1.matched_invoice_id == "101"

        res_tx2 = BankTransaction.query.filter_by(id="TX_MATCH_02").first()
        assert res_tx2.status == "matched"
        assert res_tx2.matched_invoice_id == "102"
        assert res_tx2.confidence_score == 0.7

        res_tx3 = BankTransaction.query.filter_by(id="TX_MATCH_03").first()
        assert res_tx3.status == "unreconciled"


def test_bank_apis(client, app):
    """Test ingestion, matching, and listing bank transactions via endpoints."""
    with client.session_transaction() as sess:
        sess["logged_in"] = True

    # Ingest statement via API
    csv_data = "2026-06-01,TXN1001,15000000.0,CRDT,110229384,MISA CO,Thanh toan hoa don 101\n"
    response = client.post("/api/bank/ingest", json={
        "taxpayer_mst": "0101234567",
        "file_content": csv_data,
        "bank_name": "Vietcombank",
        "file_type": "csv"
    })
    assert response.status_code == 201
    assert response.get_json()["success"] is True
    assert response.get_json()["inserted_count"] == 1

    # Match statement via API
    response = client.post("/api/bank/match", json={
        "taxpayer_mst": "0101234567"
    })
    assert response.status_code == 200
    assert response.get_json()["success"] is True

    # List bank transactions via API
    response = client.get("/api/bank/transactions?taxpayer_mst=0101234567")
    assert response.status_code == 200
    txs = response.get_json()
    assert len(txs) == 1
    assert txs[0]["id"] == "TXN1001"

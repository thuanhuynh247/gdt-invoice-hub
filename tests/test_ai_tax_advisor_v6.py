"""Tests for Local Vector DB, Tax RAG Index, and Autonomous Advisory Agent (US-094, US-095)."""

from __future__ import annotations

import pytest
from invoices.ai_tax_advisor import (
    LocalVectorStore,
    create_tax_regulation_index,
    TaxAdvisoryAgent,
    TAX_REGULATION_EXCERPTS,
)


class TestLocalVectorStore:
    """US-094: Local Vector DB Setup & Law 149/48 Tax Regulatory Index."""

    def test_add_and_index_documents(self):
        """Vector store should accept documents and build an index."""
        store = LocalVectorStore()
        store.add_document("doc1", "Thuế giá trị gia tăng GTGT")
        store.add_document("doc2", "Hóa đơn điện tử chữ ký số")
        store.build_index()

        stats = store.stats()
        assert stats["total_documents"] == 2
        assert stats["vocabulary_size"] > 0
        assert stats["indexed"] is True

    def test_query_returns_relevant_results(self):
        """Query should rank relevant documents higher."""
        store = LocalVectorStore()
        store.add_document("tax", "Thuế GTGT thuế suất 10 phần trăm giá trị gia tăng")
        store.add_document("invoice", "Hóa đơn điện tử chữ ký số bắt buộc theo Thông tư 78")
        store.add_document("penalty", "Xử phạt vi phạm thuế trốn thuế gian lận hóa đơn")
        store.build_index()

        results = store.query("thuế GTGT giá trị gia tăng", top_k=3)
        assert len(results) > 0
        # The tax document should score highest
        assert results[0]["id"] == "tax"

    def test_query_empty_store_returns_empty(self):
        """Querying an empty store should return empty results."""
        store = LocalVectorStore()
        store.build_index()
        results = store.query("bất kỳ câu hỏi nào")
        assert results == []

    def test_tokenizer_handles_vietnamese(self):
        """Tokenizer should handle Vietnamese diacritics correctly."""
        store = LocalVectorStore()
        tokens = store._tokenize("Thuế giá trị gia tăng GTGT 10%")
        assert "thuế" in tokens
        assert "giá" in tokens
        assert "gtgt" in tokens

    def test_cosine_similarity_identical_vectors(self):
        """Identical vectors should have cosine similarity = 1.0."""
        vec = [1.0, 2.0, 3.0]
        score = LocalVectorStore._cosine_similarity(vec, vec)
        assert abs(score - 1.0) < 1e-6

    def test_cosine_similarity_orthogonal_vectors(self):
        """Orthogonal vectors should have cosine similarity = 0.0."""
        vec_a = [1.0, 0.0]
        vec_b = [0.0, 1.0]
        score = LocalVectorStore._cosine_similarity(vec_a, vec_b)
        assert abs(score) < 1e-6


class TestTaxRegulationIndex:
    """US-094: Verify pre-indexed Law 48/149 excerpts."""

    def test_create_index_has_correct_document_count(self):
        """Index should contain all pre-defined regulation excerpts."""
        store = create_tax_regulation_index()
        stats = store.stats()
        assert stats["total_documents"] == len(TAX_REGULATION_EXCERPTS)
        assert stats["indexed"] is True

    def test_query_vat_deduction_returns_law48(self):
        """Querying for VAT deduction should return Law 48 references."""
        store = create_tax_regulation_index()
        results = store.query("khấu trừ thuế GTGT đầu vào hóa đơn", top_k=3)
        assert len(results) > 0
        sources = [r["source"] for r in results]
        assert any("Luật 48" in s for s in sources)

    def test_query_einvoice_returns_law149(self):
        """Querying for e-invoices should return Law 149 references."""
        store = create_tax_regulation_index()
        results = store.query("hóa đơn điện tử chữ ký số Thông tư 78", top_k=3)
        assert len(results) > 0
        sources = [r["source"] for r in results]
        assert any("Luật 149" in s for s in sources)

    def test_query_penalties_returns_relevant(self):
        """Querying for tax penalties should return relevant results."""
        store = create_tax_regulation_index()
        results = store.query("xử phạt trốn thuế gian lận", top_k=3)
        assert len(results) > 0
        # At least one result should mention penalties
        texts = " ".join(r["text"] for r in results)
        assert "phạt" in texts.lower()


class TestTaxAdvisoryAgent:
    """US-095: Autonomous Tax Advisory Agent & 23:00 Auditing Control Panel."""

    def _sample_invoices(self):
        """Return a representative set of test invoices."""
        return [
            {
                "id": "INV-CLEAN-001",
                "seller_name": "Công ty ABC",
                "seller_mst": "0109998887",
                "total_amount": 15_000_000,
                "payment_method": "Chuyển khoản",
                "t_score": 95,
                "has_signature": True,
                "date": "2026-05-01",
            },
            {
                "id": "INV-CASH-002",
                "seller_name": "Công ty XYZ",
                "seller_mst": "0112223334",
                "total_amount": 25_000_000,
                "payment_method": "Tiền mặt",
                "t_score": 80,
                "has_signature": True,
                "date": "2026-05-05",
            },
            {
                "id": "INV-NOSIG-003",
                "seller_name": "Cửa hàng DEF",
                "seller_mst": "0199887766",
                "total_amount": 5_000_000,
                "payment_method": "Chuyển khoản",
                "t_score": 75,
                "has_signature": False,
                "date": "2026-05-10",
            },
            {
                "id": "INV-RISK-004",
                "seller_name": "Công ty Phantom",
                "seller_mst": "0100000001",
                "total_amount": 50_000_000,
                "payment_method": "Tiền mặt",
                "t_score": 35,
                "has_signature": False,
                "date": "2026-05-15",
            },
        ]

    def test_scan_identifies_cash_payment_risk(self):
        """Agent should flag cash payments >= 20M VND."""
        agent = TaxAdvisoryAgent()
        findings = agent.scan_invoices(self._sample_invoices())

        cash_findings = [
            f for f in findings
            for r in f["risks"]
            if r["type"] == "CASH_PAYMENT_RISK"
        ]
        assert len(cash_findings) >= 1
        flagged_ids = [f["invoice_id"] for f in cash_findings]
        assert "INV-CASH-002" in flagged_ids

    def test_scan_identifies_missing_signature(self):
        """Agent should flag invoices without digital signatures."""
        agent = TaxAdvisoryAgent()
        findings = agent.scan_invoices(self._sample_invoices())

        sig_findings = [
            f for f in findings
            for r in f["risks"]
            if r["type"] == "MISSING_SIGNATURE"
        ]
        assert len(sig_findings) >= 1
        flagged_ids = [f["invoice_id"] for f in sig_findings]
        assert "INV-NOSIG-003" in flagged_ids

    def test_scan_identifies_low_tscore(self):
        """Agent should flag invoices with T-Score < 60."""
        agent = TaxAdvisoryAgent()
        findings = agent.scan_invoices(self._sample_invoices())

        tscore_findings = [
            f for f in findings
            for r in f["risks"]
            if r["type"] == "LOW_TSCORE_ALERT"
        ]
        assert len(tscore_findings) >= 1
        flagged_ids = [f["invoice_id"] for f in tscore_findings]
        assert "INV-RISK-004" in flagged_ids

    def test_clean_invoice_not_flagged(self):
        """Clean invoices with good T-Score, bank transfer, and signature should NOT be flagged."""
        agent = TaxAdvisoryAgent()
        findings = agent.scan_invoices(self._sample_invoices())

        flagged_ids = [f["invoice_id"] for f in findings]
        assert "INV-CLEAN-001" not in flagged_ids

    def test_generate_dossier_structure(self):
        """Generated dossier should have the correct structure and severity counts."""
        agent = TaxAdvisoryAgent()
        dossier = agent.run_audit_cycle(self._sample_invoices())

        assert "generated_at" in dossier
        assert "total_invoices_flagged" in dossier
        assert "severity_summary" in dossier
        assert "findings" in dossier
        assert "recommendation" in dossier

        # INV-RISK-004 triggers CRITICAL, HIGH, and MEDIUM risks
        assert dossier["severity_summary"]["critical"] >= 1
        assert dossier["total_invoices_flagged"] >= 3

    def test_dossier_recommendation_urgency(self):
        """Dossier with CRITICAL findings should produce urgent recommendation."""
        agent = TaxAdvisoryAgent()
        dossier = agent.run_audit_cycle(self._sample_invoices())
        assert "CẢNH BÁO KHẨN CẤP" in dossier["recommendation"]

    def test_dossier_with_no_risks(self):
        """An invoice list with no risks should produce an all-clear dossier."""
        agent = TaxAdvisoryAgent()
        clean_invoices = [
            {
                "id": "INV-OK-001",
                "seller_name": "Good Corp",
                "seller_mst": "0109998887",
                "total_amount": 10_000_000,
                "payment_method": "Chuyển khoản",
                "t_score": 95,
                "has_signature": True,
                "date": "2026-05-01",
            }
        ]
        dossier = agent.run_audit_cycle(clean_invoices)
        assert dossier["total_invoices_flagged"] == 0
        assert "bình thường" in dossier["recommendation"]

    def test_legal_refs_included_in_findings(self):
        """Each risk finding should include legal references from the vector store."""
        agent = TaxAdvisoryAgent()
        findings = agent.scan_invoices(self._sample_invoices())

        for finding in findings:
            for risk in finding["risks"]:
                assert "legal_refs" in risk
                assert len(risk["legal_refs"]) > 0
                # Legal refs should reference known law sources
                refs_text = " ".join(risk["legal_refs"])
                assert "Luật" in refs_text

"""Unit tests for Graph Fraud Detection Engine (US-330, US-331)."""

from __future__ import annotations

import pytest
from extensions import db
from invoices.models import Invoice, Partner
from invoices.graph_service import TaxpayerNetworkGraphGenerator, VATFraudRingNetworkDetector


def test_graph_generation_and_metrics(app):
    """Test directed graph creation, cycle detection, and scores computation."""
    with app.app_context():
        # Clean DB
        Invoice.query.delete()
        Partner.query.delete()
        db.session.commit()

        # Seed partners
        p_a = Partner(mst="111", name="Công ty A")
        p_b = Partner(mst="222", name="Công ty B")
        p_c = Partner(mst="333", name="Công ty C")
        db.session.add_all([p_a, p_b, p_c])

        # Seed circular invoices: A -> B -> C -> A
        inv_ab = Invoice(
            id="inv-ab", taxpayer_mst="111", seller_mst="111", buyer_mst="222",
            seller_name="Công ty A", buyer_name="Công ty B", total_amount=100000000.0,
            date="2026-06-01", imported_at="2026-06-01T00:00:00Z"
        )
        inv_bc = Invoice(
            id="inv-bc", taxpayer_mst="111", seller_mst="222", buyer_mst="333",
            seller_name="Công ty B", buyer_name="Công ty C", total_amount=100000000.0,
            date="2026-06-02", imported_at="2026-06-02T00:00:00Z"
        )
        inv_ca = Invoice(
            id="inv-ca", taxpayer_mst="111", seller_mst="333", buyer_mst="111",
            seller_name="Công ty C", buyer_name="Công ty A", total_amount=100000000.0,
            date="2026-06-03", imported_at="2026-06-03T00:00:00Z"
        )
        db.session.add_all([inv_ab, inv_bc, inv_ca])
        db.session.commit()

        # Generate Graph
        graph = TaxpayerNetworkGraphGenerator.build_network_graph("111")
        assert len(graph["nodes"]) == 3
        assert len(graph["edges"]) == 3

        # Run detector
        detector = VATFraudRingNetworkDetector(graph)
        cycles = detector.detect_cycles(max_length=5)
        assert len(cycles) == 1
        assert "111" in cycles[0]
        assert "222" in cycles[0]
        assert "333" in cycles[0]

        # Compute PageRank and HITS
        pr = detector.compute_pagerank()
        hubs, auths = detector.compute_hits()

        assert len(pr) == 3
        assert len(hubs) == 3
        assert len(auths) == 3

        # Detect alerts
        alerts = detector.detect_fraud_networks()
        assert len(alerts) >= 1
        assert alerts[0]["type"] == "circular_transaction_ring"

"""Graph Fraud Analyzer for tax networks (US-330, US-331)."""

from __future__ import annotations

import json
from invoices.models import Invoice, Partner


class TaxpayerNetworkGraphGenerator:
    """Builds a directed supplier-buyer transaction network graph from invoices."""

    @staticmethod
    def build_network_graph(taxpayer_mst: str | None = None) -> dict:
        """Constructs a directed graph representation of transactions.

        Nodes represent tax codes (MSTs) and edges represent invoice flows from Seller to Buyer.
        """
        # Fetch invoices
        query = Invoice.query
        if taxpayer_mst:
            query = query.filter(
                (Invoice.taxpayer_mst == taxpayer_mst) |
                (Invoice.seller_mst == taxpayer_mst) |
                (Invoice.buyer_mst == taxpayer_mst)
            )
        invoices = query.all()

        # Build nodes and edges
        nodes = {}  # mst -> {mst, name, role, total_sales, total_purchases}
        edges = {}  # (seller, buyer) -> {weight/count, total_amount}

        # Resolve partner names for metadata
        partners = {p.mst: p.name for p in Partner.query.all()}

        def get_or_create_node(mst: str, name: str | None):
            if mst not in nodes:
                nodes[mst] = {
                    "id": mst,
                    "name": name or partners.get(mst) or f"MST: {mst}",
                    "total_sales": 0.0,
                    "total_purchases": 0.0,
                    "sales_count": 0,
                    "purchases_count": 0,
                    "is_taxpayer": mst == taxpayer_mst
                }
            return nodes[mst]

        for inv in invoices:
            seller = inv.seller_mst
            buyer = inv.buyer_mst
            if not seller or not buyer:
                continue

            s_name = inv.seller_name
            b_name = inv.buyer_name
            amount = inv.total_amount

            # Update nodes
            s_node = get_or_create_node(seller, s_name)
            b_node = get_or_create_node(buyer, b_name)

            s_node["total_sales"] += amount
            s_node["sales_count"] += 1
            b_node["total_purchases"] += amount
            b_node["purchases_count"] += 1

            # Update edges
            edge_key = (seller, buyer)
            if edge_key not in edges:
                edges[edge_key] = {
                    "source": seller,
                    "target": buyer,
                    "count": 0,
                    "total_amount": 0.0
                }
            edges[edge_key]["count"] += 1
            edges[edge_key]["total_amount"] += amount

        return {
            "nodes": nodes,
            "edges": edges
        }


class VATFraudRingNetworkDetector:
    """Detects VAT circular invoicing rings using graph algorithms (PageRank, HITS, Cycle Detection)."""

    def __init__(self, graph_data: dict):
        self.nodes = graph_data["nodes"]
        self.edges = graph_data["edges"]

        # Adjacency representations for algorithmic processing
        self.adj = {}       # u -> set of outgoing neighbors
        self.rev_adj = {}   # u -> set of incoming neighbors

        for mst in self.nodes:
            self.adj[mst] = set()
            self.rev_adj[mst] = set()

        for (u, v) in self.edges:
            if u in self.adj:
                self.adj[u].add(v)
            if v in self.rev_adj:
                self.rev_adj[v].add(u)

    def detect_cycles(self, max_length: int = 5) -> list[list[str]]:
        """Finds directed cycles of length <= max_length (Circular invoicing detection)."""
        cycles = []
        visited_nodes = set()

        def dfs(start: str, curr: str, path: list[str]):
            if len(path) > max_length:
                return

            for nxt in self.adj.get(curr, []):
                if nxt == start and len(path) >= 2:
                    # Found cycle
                    # Canonicalize representation (start with smallest MST identifier)
                    cycle = path[:]
                    min_idx = cycle.index(min(cycle))
                    canonical = cycle[min_idx:] + cycle[:min_idx]
                    if canonical not in cycles:
                        cycles.append(canonical)
                elif nxt not in path and nxt not in visited_nodes:
                    dfs(start, nxt, path + [nxt])

        for start_node in self.nodes:
            dfs(start_node, start_node, [start_node])
            visited_nodes.add(start_node)

        return cycles

    def compute_hits(self, max_iter: int = 50, tol: float = 1e-4) -> tuple[dict[str, float], dict[str, float]]:
        """Computes HITS Hub and Authority scores for each node in the network."""
        if not self.nodes:
            return {}, {}

        hubs = {mst: 1.0 for mst in self.nodes}
        authorities = {mst: 1.0 for mst in self.nodes}

        for _ in range(max_iter):
            last_hubs = hubs.copy()
            last_auths = authorities.copy()

            # Update authorities: authority_score = sum of hub_scores of incoming neighbors
            for u in self.nodes:
                authorities[u] = sum(last_hubs[v] for v in self.rev_adj.get(u, []))

            # Update hubs: hub_score = sum of authority_scores of outgoing neighbors
            for u in self.nodes:
                hubs[u] = sum(last_auths[v] for v in self.adj.get(u, []))

            # Normalization
            sum_auth = sum(authorities.values())
            sum_hub = sum(hubs.values())

            if sum_auth > 0:
                authorities = {u: val / sum_auth for u, val in authorities.items()}
            if sum_hub > 0:
                hubs = {u: val / sum_hub for u, val in hubs.items()}

            # Convergence check
            err_hub = sum(abs(hubs[u] - last_hubs[u]) for u in self.nodes)
            err_auth = sum(abs(authorities[u] - last_auths[u]) for u in self.nodes)

            if err_hub < tol and err_auth < tol:
                break

        return hubs, authorities

    def compute_pagerank(self, d: float = 0.85, max_iter: int = 50, tol: float = 1e-4) -> dict[str, float]:
        """Computes PageRank authority score for each node in the network."""
        if not self.nodes:
            return {}

        n = len(self.nodes)
        pr = {mst: 1.0 / n for mst in self.nodes}

        for _ in range(max_iter):
            last_pr = pr.copy()
            next_pr = {mst: (1.0 - d) / n for mst in self.nodes}

            # Out degree tracker
            out_degree = {mst: len(self.adj[mst]) for mst in self.nodes}

            # Dangling nodes contribution
            dangling_sum = sum(last_pr[mst] for mst in self.nodes if out_degree[mst] == 0)

            for u in self.nodes:
                # Add distribution from dangling nodes
                next_pr[u] += d * (dangling_sum / n)

                # Collect from incoming neighbors
                for v in self.rev_adj.get(u, []):
                    if out_degree[v] > 0:
                        next_pr[u] += d * (last_pr[v] / out_degree[v])

            # Convergence check
            err = sum(abs(next_pr[u] - last_pr[u]) for u in self.nodes)
            pr = next_pr

            if err < tol:
                break

        return pr

    def detect_fraud_networks(self) -> list[dict]:
        """Runs the audit suite over the network, generating alerts for circular and authority outliers."""
        alerts = []
        cycles = self.detect_cycles(max_length=5)
        hubs, auths = self.compute_hits()
        pageranks = self.compute_pagerank()

        # Alert 1: Circular transaction loops
        for cycle in cycles:
            mst_chain = " -> ".join(cycle) + f" -> {cycle[0]}"
            alerts.append({
                "type": "circular_transaction_ring",
                "severity": "CRITICAL",
                "message": f"CẢNH BÁO: Phát hiện vòng lặp giao dịch hóa đơn khép kín (VAT Ring): {mst_chain}.",
                "involved_msts": cycle
            })

        # Alert 2: Outliers (High Hub score, High sales volume relative to active profile)
        hub_threshold = 0.4
        for mst, hub_val in hubs.items():
            if hub_val > hub_threshold and not self.nodes[mst]["is_taxpayer"]:
                alerts.append({
                    "type": "high_hub_outlier",
                    "severity": "HIGH",
                    "message": f"CẢNH BÁO: Đối tác {self.nodes[mst]['name']} ({mst}) có chỉ số Hub Score cao bất thường ({round(hub_val, 3)}), nghi vấn doanh nghiệp ma/trung gian bán hóa đơn khống.",
                    "involved_msts": [mst]
                })

        return alerts

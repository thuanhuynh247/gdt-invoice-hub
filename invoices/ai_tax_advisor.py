"""Local vector database and RAG index for Vietnamese tax regulations (US-094, US-095).

Implements a lightweight, zero-external-dependency local vector store using
numpy-based cosine similarity and simple TF-IDF vectorization. This ensures
no invoice metadata is leaked to public embedding APIs.

The autonomous advisory agent (US-095) wakes on a configurable schedule,
scans tenant ledgers for compliance risks, and compiles explanation dossiers.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Optional


# ── Local TF-IDF Vector Store ──────────────────────────────────────

class LocalVectorStore:
    """A lightweight in-memory vector store using TF-IDF and cosine similarity.

    This avoids external embedding APIs, keeping all tax regulation data local.
    """

    def __init__(self):
        self.documents: list[dict] = []  # {"id", "text", "source", "page", "vector"}
        self.vocabulary: dict[str, int] = {}
        self.idf: dict[str, float] = {}
        self._indexed = False

    def add_document(self, doc_id: str, text: str, source: str = "", page: int = 0):
        """Add a text chunk to the store."""
        self.documents.append({
            "id": doc_id,
            "text": text,
            "source": source,
            "page": page,
            "vector": None,
        })
        self._indexed = False

    def _tokenize(self, text: str) -> list[str]:
        """Simple Unicode-aware tokenizer for Vietnamese text."""
        text = text.lower()
        tokens = re.findall(r'[a-zA-ZÀ-ỹ0-9]+', text)
        return [t for t in tokens if len(t) > 1]

    def _build_vocabulary(self):
        """Build vocabulary and compute IDF scores across all documents."""
        doc_freq: Counter = Counter()
        all_tokens_per_doc = []

        for doc in self.documents:
            tokens = set(self._tokenize(doc["text"]))
            all_tokens_per_doc.append(tokens)
            for token in tokens:
                doc_freq[token] += 1

        # Build vocabulary index
        self.vocabulary = {token: idx for idx, token in enumerate(sorted(doc_freq.keys()))}

        # Compute IDF
        n_docs = len(self.documents)
        self.idf = {}
        for token, freq in doc_freq.items():
            self.idf[token] = math.log((n_docs + 1) / (freq + 1)) + 1

    def _vectorize(self, text: str) -> list[float]:
        """Convert text to a TF-IDF vector."""
        tokens = self._tokenize(text)
        tf = Counter(tokens)
        total = len(tokens) if tokens else 1

        vector = [0.0] * len(self.vocabulary)
        for token, count in tf.items():
            if token in self.vocabulary:
                idx = self.vocabulary[token]
                vector[idx] = (count / total) * self.idf.get(token, 1.0)

        return vector

    def build_index(self):
        """Build TF-IDF vectors for all documents."""
        self._build_vocabulary()
        for doc in self.documents:
            doc["vector"] = self._vectorize(doc["text"])
        self._indexed = True

    def query(self, query_text: str, top_k: int = 5) -> list[dict]:
        """Find the top-k most relevant documents for a query."""
        if not self._indexed:
            self.build_index()

        query_vector = self._vectorize(query_text)
        results = []

        for doc in self.documents:
            score = self._cosine_similarity(query_vector, doc["vector"])
            if score > 0:
                results.append({
                    "id": doc["id"],
                    "text": doc["text"][:500],
                    "source": doc["source"],
                    "page": doc["page"],
                    "score": round(score, 6),
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    @staticmethod
    def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def stats(self) -> dict:
        """Return index statistics."""
        return {
            "total_documents": len(self.documents),
            "vocabulary_size": len(self.vocabulary),
            "indexed": self._indexed,
        }


# ── Tax Regulation Indexer ─────────────────────────────────────────

# Pre-indexed regulation excerpts for Law 48 and Law 149
TAX_REGULATION_EXCERPTS = [
    {
        "id": "law48-art1-s1",
        "source": "Luật 48/2024/QH15 - Thuế GTGT",
        "page": 1,
        "text": (
            "Điều 1: Phạm vi điều chỉnh. Luật này quy định về đối tượng chịu thuế, đối tượng không chịu thuế, "
            "người nộp thuế, căn cứ tính thuế, phương pháp tính thuế giá trị gia tăng. "
            "Thuế suất thuế GTGT gồm 0%, 5%, 10%. Ngưỡng doanh thu chịu thuế GTGT "
            "là 200 triệu đồng/năm (trước đây 100 triệu). Hàng hóa nông sản chưa qua chế biến "
            "không chịu thuế GTGT theo Điều 5."
        ),
    },
    {
        "id": "law48-art5-exempt",
        "source": "Luật 48/2024/QH15 - Thuế GTGT",
        "page": 5,
        "text": (
            "Điều 5: Đối tượng không chịu thuế GTGT. Sản phẩm trồng trọt, chăn nuôi, thủy sản, hải sản "
            "chưa qua chế biến hoặc chỉ qua sơ chế thông thường. Bảo hiểm nhân thọ, bảo hiểm học sinh. "
            "Dịch vụ y tế, dịch vụ giáo dục. Vận chuyển hành khách công cộng bằng xe buýt, xe điện."
        ),
    },
    {
        "id": "law48-art8-rates",
        "source": "Luật 48/2024/QH15 - Thuế GTGT",
        "page": 8,
        "text": (
            "Điều 8: Thuế suất. Thuế suất 0% áp dụng cho hàng hóa xuất khẩu, vận tải quốc tế. "
            "Thuế suất 5% cho nước sạch sinh hoạt, sách giáo khoa, thiết bị y tế, thức ăn gia súc. "
            "Thuế suất 10% áp dụng cho hàng hóa và dịch vụ không thuộc đối tượng 0% hoặc 5%."
        ),
    },
    {
        "id": "law48-art12-deduction",
        "source": "Luật 48/2024/QH15 - Thuế GTGT",
        "page": 12,
        "text": (
            "Điều 12: Khấu trừ thuế GTGT đầu vào. Thuế GTGT đầu vào được khấu trừ khi có hóa đơn GTGT hợp pháp "
            "và chứng từ thanh toán không dùng tiền mặt cho hóa đơn có giá trị từ 20 triệu đồng trở lên. "
            "Hóa đơn từ nhà cung cấp bị đình chỉ hoạt động hoặc bỏ trốn sẽ không được khấu trừ."
        ),
    },
    {
        "id": "law149-art1-scope",
        "source": "Luật 149/2024/QH15 - Quản lý thuế",
        "page": 1,
        "text": (
            "Điều 1: Phạm vi điều chỉnh Luật Quản lý Thuế sửa đổi. Bổ sung quy định về hóa đơn điện tử, "
            "chữ ký số, và xử lý vi phạm hành chính trong lĩnh vực thuế. Cơ quan thuế có quyền truy cập "
            "dữ liệu ngân hàng để đối chiếu thu nhập chịu thuế."
        ),
    },
    {
        "id": "law149-art90-einvoice",
        "source": "Luật 149/2024/QH15 - Quản lý thuế",
        "page": 90,
        "text": (
            "Điều 90: Hóa đơn điện tử. Tổ chức, cá nhân kinh doanh phải sử dụng hóa đơn điện tử "
            "có mã của cơ quan thuế hoặc hóa đơn điện tử không có mã. Hóa đơn điện tử phải có chữ ký số "
            "và được truyền dữ liệu đến cơ quan thuế theo quy định tại Thông tư 78/2021/TT-BTC."
        ),
    },
    {
        "id": "law149-art123-penalty",
        "source": "Luật 149/2024/QH15 - Quản lý thuế",
        "page": 123,
        "text": (
            "Điều 123: Xử phạt vi phạm. Phạt tiền từ 500.000 đồng đến 8.000.000 đồng đối với hành vi "
            "không kê khai thuế đúng thời hạn. Phạt từ 20% đến 60% số tiền thuế trốn đối với hành vi "
            "trốn thuế. Trường hợp gian lận hóa đơn có thể bị truy cứu trách nhiệm hình sự."
        ),
    },
    {
        "id": "law149-art132-digital",
        "source": "Luật 149/2024/QH15 - Quản lý thuế",
        "page": 132,
        "text": (
            "Điều 132: Chuyển đổi số trong quản lý thuế. Cơ quan thuế triển khai nền tảng số hóa "
            "toàn diện bao gồm: cổng kê khai thuế điện tử, hệ thống tra cứu hóa đơn tập trung, "
            "kết nối API với phần mềm kế toán doanh nghiệp, và ứng dụng AI để phát hiện gian lận thuế."
        ),
    },
    {
        "id": "circular20-art13-employee-payment",
        "source": "Thông tư 20/2026/TT-BTC - Thuế TNDN",
        "page": 13,
        "text": (
            "Điều 13: Chi phí mua hàng ủy quyền qua cá nhân. Các giao dịch mua hàng hóa, dịch vụ được doanh nghiệp "
            "ủy quyền cho cá nhân thanh toán bằng thẻ cá nhân hoặc tiền mặt từ 5 triệu đồng trở lên "
            "(đã bao gồm thuế GTGT) để được tính vào chi phí được trừ khi tính thuế TNDN và được khấu trừ thuế GTGT "
            "phải có đầy đủ hóa đơn hợp pháp và chứng từ thanh toán không dùng tiền mặt (chuyển khoản từ tài khoản cá nhân "
            "được ủy quyền sang tài khoản người bán và doanh nghiệp hoàn trả tiền qua tài khoản ngân hàng của cá nhân đó)."
        ),
    },
]


def create_tax_regulation_index() -> LocalVectorStore:
    """Create and index a local vector store with Vietnamese tax regulation excerpts."""
    store = LocalVectorStore()
    for excerpt in TAX_REGULATION_EXCERPTS:
        store.add_document(
            doc_id=excerpt["id"],
            text=excerpt["text"],
            source=excerpt["source"],
            page=excerpt["page"],
        )
    store.build_index()
    return store


# ── Autonomous Tax Advisory Agent (US-095) ─────────────────────────

class TaxAdvisoryAgent:
    """Autonomous agent that scans invoices and generates compliance dossiers.

    In production, this agent runs as a scheduled worker (e.g., 23:00 daily).
    For testing, it can be triggered manually with `run_audit_cycle()`.
    """

    def __init__(self, vector_store: LocalVectorStore | None = None):
        self.vector_store = vector_store or create_tax_regulation_index()
        self.findings: list[dict] = []

    def scan_invoices(self, invoices: list[dict]) -> list[dict]:
        """Scan a list of invoice dicts for compliance risks.

        Each invoice dict should have keys: id, seller_name, seller_mst,
        total_amount, payment_method, t_score, has_signature, date.
        """
        self.findings = []

        for inv in invoices:
            risks = []

            # Rule 1: Cash payment above 20M VND
            if (inv.get("payment_method", "").lower() in ("tiền mặt", "tien mat", "cash", "tm")
                    and inv.get("total_amount", 0) >= 20_000_000):
                refs = self.vector_store.query("khấu trừ thuế thanh toán tiền mặt 20 triệu", top_k=2)
                risks.append({
                    "type": "CASH_PAYMENT_RISK",
                    "severity": "HIGH",
                    "message": f"Hóa đơn {inv['id']} thanh toán tiền mặt >= 20 triệu VND, không được khấu trừ thuế GTGT đầu vào.",
                    "legal_refs": [r["source"] + f" (trang {r['page']})" for r in refs],
                })

            # Rule 2: Missing digital signature
            if not inv.get("has_signature", True):
                refs = self.vector_store.query("hóa đơn điện tử chữ ký số bắt buộc", top_k=2)
                risks.append({
                    "type": "MISSING_SIGNATURE",
                    "severity": "MEDIUM",
                    "message": f"Hóa đơn {inv['id']} thiếu chữ ký số điện tử, vi phạm Thông tư 78.",
                    "legal_refs": [r["source"] + f" (trang {r['page']})" for r in refs],
                })

            # Rule 3: Low T-Score (high tax risk)
            if inv.get("t_score", 100) < 60:
                refs = self.vector_store.query("xử phạt vi phạm trốn thuế gian lận", top_k=2)
                risks.append({
                    "type": "LOW_TSCORE_ALERT",
                    "severity": "CRITICAL",
                    "message": f"Hóa đơn {inv['id']} có T-Score={inv['t_score']}, rủi ro bị thanh tra thuế cao.",
                    "legal_refs": [r["source"] + f" (trang {r['page']})" for r in refs],
                })

            # Rule 4: Employee authorized purchase >= 5M VND without non-cash payment proofs (Circular 20/2026/TT-BTC)
            is_emp_auth = (
                inv.get("is_employee_payment") or 
                inv.get("employee_payment") or 
                inv.get("is_authorized_payment") or 
                inv.get("employee_authorized") or
                any(kw in inv.get("payment_method", "").lower() for kw in ["ủy quyền", "uy quyen", "nhân viên", "nhan vien", "cá nhân", "ca nhan"])
            )
            if is_emp_auth and inv.get("total_amount", 0) >= 5_000_000 and not inv.get("has_non_cash_proof", False):
                refs = self.vector_store.query("ủy quyền thanh toán không dùng tiền mặt 5 triệu thông tư 20", top_k=2)
                risks.append({
                    "type": "CIT_CIRCULAR_20_RISK",
                    "severity": "HIGH",
                    "message": (
                        f"Hóa đơn {inv['id']} mua hàng ủy quyền qua cá nhân từ 5 triệu đồng trở lên "
                        "nhưng thiếu chứng từ thanh toán không dùng tiền mặt theo Điều 13 Thông tư 20/2026/TT-BTC."
                    ),
                    "legal_refs": [r["source"] + f" (trang {r['page']})" for r in refs],
                })

            if risks:
                self.findings.append({
                    "invoice_id": inv["id"],
                    "seller": inv.get("seller_name", "N/A"),
                    "seller_mst": inv.get("seller_mst", "N/A"),
                    "risks": risks,
                })

        return self.findings

    def generate_dossier(self) -> dict:
        """Generate a compliance advisory dossier from the latest scan findings."""
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        critical = sum(1 for f in self.findings for r in f["risks"] if r["severity"] == "CRITICAL")
        high = sum(1 for f in self.findings for r in f["risks"] if r["severity"] == "HIGH")
        medium = sum(1 for f in self.findings for r in f["risks"] if r["severity"] == "MEDIUM")

        return {
            "generated_at": now,
            "total_invoices_flagged": len(self.findings),
            "severity_summary": {
                "critical": critical,
                "high": high,
                "medium": medium,
            },
            "findings": self.findings,
            "recommendation": self._generate_recommendation(critical, high, medium),
        }

    def _generate_recommendation(self, critical: int, high: int, medium: int) -> str:
        """Generate a human-readable recommendation based on severity counts."""
        if critical > 0:
            return (
                f"CẢNH BÁO KHẨN CẤP: Phát hiện {critical} hóa đơn có rủi ro nghiêm trọng (CRITICAL). "
                "Đề nghị CFO xem xét ngay và chuẩn bị hồ sơ giải trình cho cơ quan thuế."
            )
        if high > 0:
            return (
                f"Phát hiện {high} hóa đơn có rủi ro cao (HIGH). "
                "Khuyến nghị kế toán trưởng rà soát lại phương thức thanh toán và bổ sung chứng từ."
            )
        if medium > 0:
            return (
                f"Phát hiện {medium} cảnh báo mức trung bình (MEDIUM). "
                "Đề nghị kiểm tra chữ ký số và hoàn thiện hồ sơ hóa đơn."
            )
        return "Không phát hiện rủi ro tuân thủ thuế. Hệ thống hoạt động bình thường."

    def run_audit_cycle(self, invoices: list[dict]) -> dict:
        """Execute a full autonomous audit cycle: scan → generate dossier."""
        self.scan_invoices(invoices)
        return self.generate_dossier()

"""Comprehensive E-Invoice Provider Registry for Vietnamese Tax System.

Maps provider tax codes (MSTTCGP) to display names, icons, colors, and lookup URLs.
This is the single source of truth for all provider metadata used by both the
backend API and the frontend UI.
"""

from __future__ import annotations

# --- Provider Display Metadata ---
# Each entry: MST -> {name, short, icon, color, url}
# icon: Bootstrap Icons class name (without 'bi-' prefix)
# color: HSL-based accent color for badges

PROVIDER_REGISTRY: dict[str, dict] = {
    # === Major Providers ===
    "0101243150": {
        "name": "MISA meInvoice",
        "short": "MISA",
        "icon": "cpu-fill",
        "color": "#67e8f9",
        "bg": "info",
    },
    "0100684378": {
        "name": "VNPT E-Invoice",
        "short": "VNPT",
        "icon": "globe",
        "color": "#60a5fa",
        "bg": "primary",
    },
    "0101360697": {
        "name": "BKAV eHoadon",
        "short": "BKAV",
        "icon": "shield-shaded",
        "color": "#f87171",
        "bg": "danger",
    },
    "0100109106": {
        "name": "Viettel VinVoice",
        "short": "Viettel",
        "icon": "telephone-fill",
        "color": "#4ade80",
        "bg": "success",
    },
    "0105987432": {
        "name": "Softdreams EasyInvoice",
        "short": "EasyInvoice",
        "icon": "lightning-fill",
        "color": "#facc15",
        "bg": "warning",
    },
    "0105232093": {
        "name": "CyberBill",
        "short": "CyberBill",
        "icon": "cloud-check-fill",
        "color": "#e2e8f0",
        "bg": "secondary",
    },
    "0100727825": {
        "name": "FAST E-Invoice",
        "short": "FAST",
        "icon": "speedometer2",
        "color": "#c084fc",
        "bg": "primary",
    },
    "0100686209": {
        "name": "MobiFone Invoice",
        "short": "MobiFone",
        "icon": "reception-4",
        "color": "#38bdf8",
        "bg": "info",
    },

    # === Medium Providers ===
    "0100100417-007": {
        "name": "Payoo EVN",
        "short": "Payoo",
        "icon": "plug-fill",
        "color": "#fb923c",
        "bg": "warning",
    },
    "0100687474": {
        "name": "PTP Invoice",
        "short": "PTP",
        "icon": "receipt",
        "color": "#a78bfa",
        "bg": "primary",
    },
    "0101162173": {
        "name": "Asia Invoice",
        "short": "AsiaInv",
        "icon": "globe-asia-australia",
        "color": "#34d399",
        "bg": "success",
    },
    "0101289966": {
        "name": "E-Hoadon Cloud",
        "short": "eHDCloud",
        "icon": "cloud-fill",
        "color": "#93c5fd",
        "bg": "info",
    },
    "0101300842": {
        "name": "EInvoice.vn",
        "short": "EInvoice",
        "icon": "file-earmark-check",
        "color": "#6ee7b7",
        "bg": "success",
    },
    "0101352495": {
        "name": "VN Invoice (v50)",
        "short": "VNInvoice",
        "icon": "file-earmark-text",
        "color": "#fca5a5",
        "bg": "danger",
    },
    "0101659906": {
        "name": "Kaike Invoice",
        "short": "Kaike",
        "icon": "journal-check",
        "color": "#fcd34d",
        "bg": "warning",
    },
    "0102182292": {
        "name": "VNPAY E-Invoice",
        "short": "VNPAY",
        "icon": "credit-card-fill",
        "color": "#818cf8",
        "bg": "primary",
    },
    "0102454468": {
        "name": "Tax24",
        "short": "Tax24",
        "icon": "calculator-fill",
        "color": "#fb7185",
        "bg": "danger",
    },
    "0102519041": {
        "name": "iHoadon.vn",
        "short": "iHoadon",
        "icon": "file-earmark-fill",
        "color": "#2dd4bf",
        "bg": "success",
    },
    "102519041": {
        "name": "iHoadon.vn",
        "short": "iHoadon",
        "icon": "file-earmark-fill",
        "color": "#2dd4bf",
        "bg": "success",
    },
    "0103018807": {
        "name": "ABCSys Invoice",
        "short": "ABCSys",
        "icon": "building",
        "color": "#a3e635",
        "bg": "success",
    },
    "0103019524": {
        "name": "AITS E-Invoice",
        "short": "AITS",
        "icon": "gear-fill",
        "color": "#d4d4d8",
        "bg": "secondary",
    },
    "0103770970": {
        "name": "Bitware Invoice",
        "short": "Bitware",
        "icon": "cpu",
        "color": "#f0abfc",
        "bg": "primary",
    },
    "0103930279": {
        "name": "NacenComm (Logigo)",
        "short": "Logigo",
        "icon": "truck",
        "color": "#fdba74",
        "bg": "warning",
    },
    "0104128565": {
        "name": "FTG Hoadon",
        "short": "FTG",
        "icon": "file-earmark-ruled",
        "color": "#86efac",
        "bg": "success",
    },
    "0104359717": {
        "name": "KiotViet Invoice",
        "short": "KiotViet",
        "icon": "shop",
        "color": "#22d3ee",
        "bg": "info",
    },
    "0104614692": {
        "name": "TVAN Invoice",
        "short": "TVAN",
        "icon": "server",
        "color": "#a5b4fc",
        "bg": "primary",
    },
    "0104908371": {
        "name": "ACMAN E-Invoice",
        "short": "ACMAN",
        "icon": "person-check-fill",
        "color": "#fca5a5",
        "bg": "danger",
    },
    "0105844836": {
        "name": "VinVoice",
        "short": "VinVoice",
        "icon": "patch-check-fill",
        "color": "#4ade80",
        "bg": "success",
    },
    "0105937449": {
        "name": "NewInvoice",
        "short": "NewInv",
        "icon": "file-earmark-plus",
        "color": "#67e8f9",
        "bg": "info",
    },
    "0105958921": {
        "name": "CloudInvoice",
        "short": "CloudInv",
        "icon": "cloud-arrow-up",
        "color": "#7dd3fc",
        "bg": "info",
    },
    "0106026495": {
        "name": "M-Invoice",
        "short": "MInvoice",
        "icon": "phone",
        "color": "#c4b5fd",
        "bg": "primary",
    },
    "0106026495-001": {
        "name": "M-Invoice (001)",
        "short": "MInvoice",
        "icon": "phone",
        "color": "#c4b5fd",
        "bg": "primary",
    },
    "0106249501": {
        "name": "M-Invoice (MST2)",
        "short": "MInvoice",
        "icon": "phone",
        "color": "#c4b5fd",
        "bg": "primary",
    },
    "0106361479": {
        "name": "A-Hoadon",
        "short": "AHoadon",
        "icon": "file-earmark-medical",
        "color": "#fbbf24",
        "bg": "warning",
    },
    "0106713804": {
        "name": "HiLo Invoice (78)",
        "short": "HiLo78",
        "icon": "bar-chart-line-fill",
        "color": "#a78bfa",
        "bg": "primary",
    },
    "0106820789": {
        "name": "Hoadondientu VN",
        "short": "HDDTVN",
        "icon": "flag-fill",
        "color": "#f472b6",
        "bg": "danger",
    },
    "0106858609": {
        "name": "VETC Invoice",
        "short": "VETC",
        "icon": "car-front-fill",
        "color": "#4ade80",
        "bg": "success",
    },
    "0106870211": {
        "name": "VietInvoice",
        "short": "VietInv",
        "icon": "patch-check",
        "color": "#38bdf8",
        "bg": "info",
    },
    "0107500414": {
        "name": "VETC (MST2)",
        "short": "VETC",
        "icon": "car-front-fill",
        "color": "#4ade80",
        "bg": "success",
    },
    "0108516079": {
        "name": "3A Soft Invoice",
        "short": "3ASoft",
        "icon": "box",
        "color": "#d4d4d8",
        "bg": "secondary",
    },
    "0108971656": {
        "name": "MyInvoice",
        "short": "MyInv",
        "icon": "person-badge",
        "color": "#fda4af",
        "bg": "danger",
    },
    "0109266456": {
        "name": "Giao Thông Số (MTC)",
        "short": "GTS",
        "icon": "signpost-split-fill",
        "color": "#67e8f9",
        "bg": "info",
    },
    "0109282176": {
        "name": "VinInvoice",
        "short": "VinInv",
        "icon": "patch-check-fill",
        "color": "#86efac",
        "bg": "success",
    },
    "0200638946": {
        "name": "O-Invoice",
        "short": "OInvoice",
        "icon": "circle-fill",
        "color": "#fcd34d",
        "bg": "warning",
    },
    "0200784873": {
        "name": "PMBK Invoice",
        "short": "PMBK",
        "icon": "mortarboard-fill",
        "color": "#c084fc",
        "bg": "primary",
    },
    "0201802839": {
        "name": "Homecasta Invoice",
        "short": "Homecasta",
        "icon": "house-fill",
        "color": "#f97316",
        "bg": "warning",
    },
    "0202029650": {
        "name": "PMBK HDBK",
        "short": "HDBK",
        "icon": "mortarboard",
        "color": "#c084fc",
        "bg": "primary",
    },
    "0301448733": {
        "name": "ACCNet Invoice",
        "short": "ACCNet",
        "icon": "hdd-network-fill",
        "color": "#34d399",
        "bg": "success",
    },
    "0301452923": {
        "name": "LienSon Invoice",
        "short": "LienSon",
        "icon": "layers-fill",
        "color": "#f0abfc",
        "bg": "primary",
    },
    "0302431595": {
        "name": "Hoadon 30s",
        "short": "HD30s",
        "icon": "stopwatch-fill",
        "color": "#facc15",
        "bg": "warning",
    },
    "0302712571": {
        "name": "MatBao Invoice",
        "short": "MatBao",
        "icon": "shield-fill",
        "color": "#818cf8",
        "bg": "primary",
    },
    "0302999571": {
        "name": "LCS EIP Invoice",
        "short": "LCS",
        "icon": "laptop",
        "color": "#d4d4d8",
        "bg": "secondary",
    },
    "0303430876": {
        "name": "TraHoadon.vn",
        "short": "TraHD",
        "icon": "search",
        "color": "#a5b4fc",
        "bg": "primary",
    },
    "0303609305": {
        "name": "iHoadonDienTu",
        "short": "iHDDT",
        "icon": "file-earmark-lock2-fill",
        "color": "#34d399",
        "bg": "success",
    },
    "0305028479": {
        "name": "E-Invoice Corp",
        "short": "E-Invoice",
        "icon": "building",
        "color": "#22d3ee",
        "bg": "info",
    },
    "0305795054": {
        "name": "PVOIL Invoice",
        "short": "PVOIL",
        "icon": "fuel-pump-fill",
        "color": "#fb923c",
        "bg": "warning",
    },
    "0306784030": {
        "name": "eHoadon Online",
        "short": "eHDOnl",
        "icon": "wifi",
        "color": "#67e8f9",
        "bg": "info",
    },
    "0309478306": {
        "name": "XuatHoaDon",
        "short": "XuatHD",
        "icon": "box-arrow-right",
        "color": "#a78bfa",
        "bg": "primary",
    },
    "0309612872": {
        "name": "SmartSign Invoice",
        "short": "SmartSign",
        "icon": "pen-fill",
        "color": "#f472b6",
        "bg": "danger",
    },
    "0310151739": {
        "name": "YoInvoice",
        "short": "YoInv",
        "icon": "emoji-smile-fill",
        "color": "#fbbf24",
        "bg": "warning",
    },
    "0310768095": {
        "name": "HDDTLink",
        "short": "HDDTLink",
        "icon": "link-45deg",
        "color": "#d4d4d8",
        "bg": "secondary",
    },
    "0310926922": {
        "name": "EHCM Invoice",
        "short": "EHCM",
        "icon": "geo-alt-fill",
        "color": "#fb7185",
        "bg": "danger",
    },
    "0311928954": {
        "name": "VietInfo Invoice",
        "short": "VietInfo",
        "icon": "info-circle-fill",
        "color": "#38bdf8",
        "bg": "info",
    },
    "0311942758": {
        "name": "NgoGiaPhat Invoice",
        "short": "NGP",
        "icon": "tools",
        "color": "#86efac",
        "bg": "success",
    },
    "0312270160": {
        "name": "AME Invoice",
        "short": "AME",
        "icon": "asterisk",
        "color": "#fca5a5",
        "bg": "danger",
    },
    "0312303803": {
        "name": "WinInvoice",
        "short": "WinInv",
        "icon": "windows",
        "color": "#60a5fa",
        "bg": "primary",
    },
    "0312942260": {
        "name": "iHoaDonDienTu.net",
        "short": "iHDDT.net",
        "icon": "globe2",
        "color": "#34d399",
        "bg": "success",
    },
    "0312961577": {
        "name": "BenThanh Invoice",
        "short": "BenThanh",
        "icon": "building",
        "color": "#fdba74",
        "bg": "warning",
    },
    "0313844107": {
        "name": "Voice HDDT",
        "short": "Voice",
        "icon": "mic-fill",
        "color": "#c4b5fd",
        "bg": "primary",
    },
    "0313906508": {
        "name": "NguyenMinhVAT",
        "short": "NMV",
        "icon": "person-fill",
        "color": "#6ee7b7",
        "bg": "success",
    },
    "0313950909": {
        "name": "Koffi Invoice",
        "short": "Koffi",
        "icon": "cup-hot-fill",
        "color": "#d97706",
        "bg": "warning",
    },
    "0313963672": {
        "name": "KKVAT Invoice",
        "short": "KKVAT",
        "icon": "key-fill",
        "color": "#a78bfa",
        "bg": "primary",
    },
    "0314185087": {
        "name": "OnlineVina Invoice",
        "short": "OnVina",
        "icon": "globe-americas",
        "color": "#22d3ee",
        "bg": "info",
    },
    "0314209362": {
        "name": "HoaDonDienTuVAT",
        "short": "HDDTVAT",
        "icon": "file-earmark-richtext",
        "color": "#f0abfc",
        "bg": "primary",
    },
    "0314743623": {
        "name": "eHoaDonDienTu",
        "short": "eHDDT",
        "icon": "lightning-charge",
        "color": "#fcd34d",
        "bg": "warning",
    },
    "0315151651": {
        "name": "PVS Solution",
        "short": "PVS",
        "icon": "hdd-stack-fill",
        "color": "#d4d4d8",
        "bg": "secondary",
    },
    "0315191291": {
        "name": "HoaDonSoVN eVAT",
        "short": "HDSoVN",
        "icon": "file-binary-fill",
        "color": "#4ade80",
        "bg": "success",
    },
    "0315298333": {
        "name": "TCT Invoice",
        "short": "TCT",
        "icon": "bank2",
        "color": "#fb923c",
        "bg": "warning",
    },
    "0315467091": {
        "name": "ACCOnline Invoice",
        "short": "ACCOnl",
        "icon": "laptop-fill",
        "color": "#93c5fd",
        "bg": "info",
    },
    "0315638251": {
        "name": "HT Invoice",
        "short": "HTInv",
        "icon": "hdd-fill",
        "color": "#a3e635",
        "bg": "success",
    },
    "0316642395": {
        "name": "PhuongNam eVAT",
        "short": "PNam",
        "icon": "compass-fill",
        "color": "#fb7185",
        "bg": "danger",
    },
    "0400462489": {
        "name": "TuanChau E-Invoice",
        "short": "TuanChau",
        "icon": "water",
        "color": "#38bdf8",
        "bg": "info",
    },
    "0401486901": {
        "name": "VIN-Hoadon",
        "short": "VIN-HD",
        "icon": "vinyl-fill",
        "color": "#c084fc",
        "bg": "primary",
    },
    "0110269067": {
        "name": "GSM HiLo E-Invoice",
        "short": "GSM-HiLo",
        "icon": "bar-chart-line",
        "color": "#a78bfa",
        "bg": "primary",
    },
    "0110269067-002": {
        "name": "GSM HiLo E-Invoice (002)",
        "short": "GSM-HiLo",
        "icon": "bar-chart-line",
        "color": "#a78bfa",
        "bg": "primary",
    },
}


def get_provider_info(msttcgp: str) -> dict:
    """Get display metadata for a provider tax code.

    Returns a dict with keys: name, short, icon, color, bg.
    If unknown, returns a generic 'Khác' entry.
    """
    if not msttcgp:
        return {"name": "", "short": "", "icon": "receipt", "color": "#94a3b8", "bg": "secondary"}

    clean = msttcgp.strip()
    info = PROVIDER_REGISTRY.get(clean)
    if info:
        return info

    return {
        "name": f"Nhà cung cấp ({clean})",
        "short": "Khác",
        "icon": "receipt",
        "color": "#94a3b8",
        "bg": "secondary",
    }


def get_all_providers() -> list[dict]:
    """Return list of all known providers for frontend consumption."""
    result = []
    for mst, info in PROVIDER_REGISTRY.items():
        result.append({
            "mst": mst,
            **info,
        })
    return result


def get_provider_stats_from_invoices(invoices) -> list[dict]:
    """Calculate provider distribution statistics from a list of invoices.

    Each invoice should have a 'msttcgp' attribute or key.
    Returns sorted list of {mst, name, short, icon, color, bg, count, total_amount}.
    """
    stats: dict[str, dict] = {}

    for inv in invoices:
        mst = ""
        if hasattr(inv, "msttcgp"):
            mst = inv.msttcgp or ""
        elif isinstance(inv, dict):
            mst = inv.get("msttcgp", "")

        mst = mst.strip() if mst else ""
        if not mst:
            mst = "__unknown__"

        if mst not in stats:
            info = get_provider_info(mst if mst != "__unknown__" else "")
            stats[mst] = {
                "mst": mst if mst != "__unknown__" else "",
                **info,
                "count": 0,
                "total_amount": 0.0,
            }

        stats[mst]["count"] += 1

        amount = 0.0
        if hasattr(inv, "amount"):
            try:
                amount = float(inv.amount or 0)
            except (ValueError, TypeError):
                pass
        elif isinstance(inv, dict):
            try:
                amount = float(inv.get("amount", 0) or 0)
            except (ValueError, TypeError):
                pass

        stats[mst]["total_amount"] += amount

    result = sorted(stats.values(), key=lambda x: x["count"], reverse=True)
    return result

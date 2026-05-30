"""GDT Tax Payment Slip Scaffolder & VietQR Generator (US-202).

Resolves Chapter and Sub-Chapter codes, constructs GDT Form 711/MB XML,
and generates standard NAPAS-compliant VietQR strings.
"""

from __future__ import annotations

import base64
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime

# GDT Sub-Chapter Codes (Tiểu mục)
SUB_CHAPTER_MAPPING = {
    "vat": "1701",        # Thuế GTGT hàng sản xuất kinh doanh trong nước
    "cit": "1052",        # Thuế thu nhập doanh nghiệp
    "pit": "1001",        # Thuế thu nhập cá nhân
    "import": "1901",     # Thuế nhập khẩu
    "env": "2001"         # Thuế bảo vệ môi trường
}

# Standard corporate chapter codes based on enterprise type
CHAPTER_MAPPING = {
    "foreign_invested": "152",  # Các doanh nghiệp có vốn đầu tư nước ngoài
    "domestic_private": "552",  # Các công ty cổ phần, TNHH tư nhân
    "domestic_other": "757"     # Hợp tác xã, tổ hợp tác
}

def crc16_ccitt(data: str) -> str:
    """Calculate CRC-16/CCITT-FALSE (0xFFFF initialization) for EMVCo/VietQR compliance."""
    crc = 0xFFFF
    for char in data:
        crc ^= ord(char) << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1
            crc &= 0xFFFF
    return f"{crc:04X}"

def generate_vietqr_string(
    bank_bin: str,
    account_number: str,
    amount: float,
    description: str
) -> str:
    """Build a standard EMVCo/NAPAS compliant VietQR string."""
    # 00: Payload Format Indicator (Fixed '01')
    qr = "000201"
    # 01: Point of Initiation Method ('11' for static, '12' for dynamic)
    qr += "010212"
    
    # 38: Merchant Account Information (NAPAS Template)
    # Sub-field 00: GUID (Fixed 'A000000727')
    # Sub-field 01: Bank BIN (6 digits)
    # Sub-field 02: Account Number (variable length)
    napas_sub = f"0010A00000072701{len(bank_bin):02d}{bank_bin}02{len(account_number):02d}{account_number}"
    qr += f"38{len(napas_sub):02d}{napas_sub}"
    
    # 53: Transaction Currency (VND is '704')
    qr += "5303704"
    
    # 54: Transaction Amount
    amt_str = f"{amount:.0f}"
    qr += f"54{len(amt_str):02d}{amt_str}"
    
    # 58: Country Code ('VN')
    qr += "5802VN"
    
    # 59: Merchant Name (e.g. KHO BAC NHA NUOC)
    merchant_name = "KHO BAC NHA NUOC"
    qr += f"59{len(merchant_name):02d}{merchant_name}"
    
    # 62: Additional Data Field Template
    # Sub-field 08: Narration / Purpose of transaction
    desc_clean = "".join(c for c in description if c.isalnum() or c in " :/-").upper()
    add_data_sub = f"08{len(desc_clean):02d}{desc_clean}"
    qr += f"62{len(add_data_sub):02d}{add_data_sub}"
    
    # 63: CRC-16 Checksum
    qr += "6304"
    checksum = crc16_ccitt(qr)
    qr += checksum
    
    return qr

def get_mock_qr_image_base64() -> str:
    """Return a tiny valid 1x1 black pixel PNG image in base64 format for testing."""
    return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

def generate_tax_payment_slip(
    mst: str,
    company_name: str,
    tax_type: str,
    amount: float,
    chapter_type: str = "domestic_private",
    treasury_name: str = "Kho bạc Nhà nước Quận Cầu Giấy",
    treasury_account: str = "111222333444",
    bank_bin: str = "970415" # VietinBank (commonly used for State Treasury)
) -> dict:
    """Generate GDT Form 711/MB Tax Payment Slip XML and VietQR code.
    
    Returns:
        {
            "xml": str,
            "vietqr_string": str,
            "vietqr_base64": str,
            "chapter_code": str,
            "sub_chapter_code": str
        }
    """
    chapter_code = CHAPTER_MAPPING.get(chapter_type, "552")
    sub_chapter_code = SUB_CHAPTER_MAPPING.get(tax_type.lower(), "1701")
    
    # Generate XML conforming to GDT e-Tax Form 711/MB schema
    root = ET.Element("GiayNopTien")
    
    header = ET.SubElement(root, "Header")
    ET.SubElement(header, "MauSo").text = "711/MB"
    ET.SubElement(header, "KyHieu").text = "GNT/2026"
    ET.SubElement(header, "NgayLap").text = datetime.now().strftime("%Y-%m-%d")
    
    taxpayer = ET.SubElement(root, "NguoiNopThue")
    ET.SubElement(taxpayer, "MaMST").text = mst
    ET.SubElement(taxpayer, "TenNNT").text = company_name
    
    treasury = ET.SubElement(root, "KhoBacNhan")
    ET.SubElement(treasury, "TenKB").text = treasury_name
    ET.SubElement(treasury, "SoTaiKhoan").text = treasury_account
    
    details = ET.SubElement(root, "ChiTietThue")
    ET.SubElement(details, "Chuong").text = chapter_code
    ET.SubElement(details, "TieuMuc").text = sub_chapter_code
    ET.SubElement(details, "SoTien").text = f"{amount:.0f}"
    ET.SubElement(details, "DienGiai").text = f"Nop thue {tax_type.upper()} ky 2026"
    
    raw_xml = ET.tostring(root, encoding="utf-8")
    parsed = minidom.parseString(raw_xml)
    xml_str = parsed.toprettyxml(indent="  ")
    
    # Generate VietQR
    narration = f"ND: MST {mst} NOP THUE TM {sub_chapter_code} C {chapter_code}"
    vietqr_str = generate_vietqr_string(
        bank_bin=bank_bin,
        account_number=treasury_account,
        amount=amount,
        description=narration
    )
    
    return {
        "xml": xml_str,
        "vietqr_string": vietqr_str,
        "vietqr_base64": get_mock_qr_image_base64(),
        "chapter_code": chapter_code,
        "sub_chapter_code": sub_chapter_code
    }

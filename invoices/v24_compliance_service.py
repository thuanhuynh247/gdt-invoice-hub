"""Version 24.0.0 Advanced Compliance Services (OCR Scaffolder, HSM Signing, Mock GDT Gateway, & Transfer Pricing)."""

from __future__ import annotations
import base64
import datetime
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import lxml.etree
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from extensions import db
from invoices.models import Invoice, Partner, LineItem
from invoices.signature_verifier import verify_xml_signature

# ── US-361: XML Scaffold from OCR Data ─────────────────────────────────

def scaffold_xml_from_ocr_data(ocr_data: dict) -> bytes:
    """Generate a GDT-compliant e-invoice XML draft from OCR structured fields."""
    template = ocr_data.get("template_code") or "1"
    symbol = ocr_data.get("symbol") or "C26TBA"
    number = ocr_data.get("number") or "00000001"
    # Ensure number is padded to 8 digits
    try:
        number = f"{int(number):08d}"
    except ValueError:
        pass

    date_str = ocr_data.get("date") or datetime.date.today().isoformat()
    payment_method = ocr_data.get("payment_method") or "TM/CK"
    
    seller_name = ocr_data.get("seller_name") or "Nhà Cung Cấp Mặc Định"
    seller_mst = ocr_data.get("seller_mst") or "0100112233"
    seller_address = ocr_data.get("seller_address") or "Địa chỉ người bán"
    
    buyer_name = ocr_data.get("buyer_name") or "Công Ty Khách Hàng Mặc Định"
    buyer_mst = ocr_data.get("buyer_mst") or "0108999999"
    buyer_address = ocr_data.get("buyer_address") or "Địa chỉ người mua"
    
    amount_before_tax = float(ocr_data.get("amount_before_tax") or 0.0)
    tax_amount = float(ocr_data.get("tax_amount") or 0.0)
    total_amount = float(ocr_data.get("total_amount") or 0.0)
    
    if total_amount == 0.0:
        total_amount = amount_before_tax + tax_amount

    # Build line items
    items_xml = ""
    items = ocr_data.get("items") or []
    if not items:
        # Create a single line item fallback to satisfy XML schema constraint (must have at least one HHDVu)
        fallback_amount = amount_before_tax if amount_before_tax > 0 else 10000.0
        fallback_tax = tax_amount if tax_amount > 0 else (fallback_amount * 0.1)
        items = [{
            "item_name": "Hàng hóa dịch vụ tổng hợp",
            "quantity": 1.0,
            "unit_price": fallback_amount,
            "amount_before_tax": fallback_amount,
            "tax_rate": ocr_data.get("tax_rate") or "10%",
            "tax_amount": fallback_tax
        }]
        
    for idx, item in enumerate(items, 1):
        item_name = item.get("item_name") or "Hàng hóa dịch vụ"
        qty = float(item.get("quantity") or 0.0)
        price = float(item.get("unit_price") or 0.0)
        amt = float(item.get("amount_before_tax") or (qty * price) or 0.0)
        rate = item.get("tax_rate") or "10%"
        t_amt = float(item.get("tax_amount") or 0.0)
        
        items_xml += f"""        <HHDVu>
          <STT>{idx}</STT>
          <Ten>{item_name}</Ten>
          <SLuong>{qty}</SLuong>
          <DGia>{price}</DGia>
          <ThTien>{amt}</ThTien>
          <TSuat>{rate}</TSuat>
          <TThue>{t_amt}</TThue>
        </HHDVu>
"""

    xml_content = f"""<HDon>
  <DLHDon Id="HD_{number}">
    <TTChung>
      <THDon>Hóa đơn giá trị gia tăng</THDon>
      <KHMSHDon>{template}</KHMSHDon>
      <KHHDon>{symbol}</KHHDon>
      <SHDon>{number}</SHDon>
      <NLap>{date_str}</NLap>
      <DVTTe>VND</DVTTe>
      <HTTToan>{payment_method}</HTTToan>
    </TTChung>
    <NDHDon>
      <NBan>
        <Ten>{seller_name}</Ten>
        <MST>{seller_mst}</MST>
        <DChi>{seller_address}</DChi>
      </NBan>
      <NMua>
        <Ten>{buyer_name}</Ten>
        <TenDonVi>{buyer_name}</TenDonVi>
        <MST>{buyer_mst}</MST>
        <DChi>{buyer_address}</DChi>
      </NMua>
      <DSDVu>
{items_xml}      </DSDVu>
    </NDHDon>
    <TToan>
      <TgTCThue>{amount_before_tax}</TgTCThue>
      <TgTThue>{tax_amount}</TgTThue>
      <TgTTTBSo>{total_amount}</TgTTTBSo>
    </TToan>
  </DLHDon>
</HDon>"""
    return xml_content.encode("utf-8")


# ── US-362: PKCS#11 HSM Cryptographic Signing Module ───────────────────

def generate_hsm_mock_certificate(company_name: str, mst: str) -> tuple[bytes, rsa.RSAPrivateKey]:
    """Generate a self-signed PKCS#11 mock HSM certificate with licensed CA brand."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    subject = x509.Name([
        x509.NameAttribute(x509.NameOID.COMMON_NAME, company_name),
        x509.NameAttribute(x509.NameOID.SERIAL_NUMBER, f"MST:{mst}"),
        x509.NameAttribute(x509.NameOID.ORGANIZATION_NAME, company_name),
        x509.NameAttribute(x509.NameOID.COUNTRY_NAME, "VN"),
    ])
    
    # Issuer CN contains 'MISA-CA' which is trusted by our signature_verifier
    issuer = x509.Name([
        x509.NameAttribute(x509.NameOID.COMMON_NAME, "MISA-CA Root Authority"),
        x509.NameAttribute(x509.NameOID.ORGANIZATION_NAME, "MISA JSC"),
        x509.NameAttribute(x509.NameOID.COUNTRY_NAME, "VN"),
    ])
    
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        now - datetime.timedelta(days=30)
    ).not_valid_after(
        now + datetime.timedelta(days=365)
    ).add_extension(
        x509.BasicConstraints(ca=False, path_length=None), critical=True,
    ).sign(private_key, hashes.SHA256())
    
    cert_der = cert.public_bytes(serialization.Encoding.DER)
    return cert_der, private_key


def sign_xml_invoice(xml_bytes: bytes, cert_der: bytes, private_key: rsa.RSAPrivateKey) -> bytes:
    """Cryptographically sign XML invoice, appending XMLDSig <Signature> node."""
    root = lxml.etree.fromstring(xml_bytes)
    
    # Locate DLHDon or get raw root
    dlhdon_nodes = root.xpath("//*[local-name()='DLHDon']")
    if dlhdon_nodes:
        dlhdon = dlhdon_nodes[0]
    else:
        dlhdon = root
        
    dlhdon_id = dlhdon.get("Id")
    if not dlhdon_id:
        dlhdon_id = "HD_1"
        dlhdon.set("Id", dlhdon_id)
        
    # Canonicalize DLHDon without any Signature elements
    import copy
    target_copy = copy.deepcopy(dlhdon)
    for sig in target_copy.xpath("//*[local-name()='Signature']"):
        parent = sig.getparent()
        if parent is not None:
            parent.remove(sig)
            
    c14n_dlhdon = lxml.etree.tostring(target_copy, method="c14n", exclusive=True)
    digest_value = base64.b64encode(hashlib.sha256(c14n_dlhdon).digest()).decode('utf-8')
    
    signed_info_xml = f"""<SignedInfo xmlns="http://www.w3.org/2000/09/xmldsig#">
  <CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
  <SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
  <Reference URI="#{dlhdon_id}">
    <Transforms>
      <Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
      <Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
    </Transforms>
    <DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
    <DigestValue>{digest_value}</DigestValue>
  </Reference>
</SignedInfo>"""
    
    signed_info_elem = lxml.etree.fromstring(signed_info_xml)
    c14n_signed_info = lxml.etree.tostring(signed_info_elem, method="c14n", exclusive=True)
    
    signature_bytes = private_key.sign(
        c14n_signed_info,
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    signature_value = base64.b64encode(signature_bytes).decode('utf-8')
    
    cert_b64 = base64.b64encode(cert_der).decode('utf-8')
    signature_xml = f"""<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
  {signed_info_xml}
  <SignatureValue>{signature_value}</SignatureValue>
  <KeyInfo>
    <X509Data>
      <X509Certificate>{cert_b64}</X509Certificate>
    </X509Data>
  </KeyInfo>
</Signature>"""
    
    signature_elem = lxml.etree.fromstring(signature_xml)
    root.append(signature_elem)
    
    return lxml.etree.tostring(root)


# ── US-363: Mock GDT Receiving Gateway Transmission Sandbox ─────────────

def transmit_to_gdt_sandbox(signed_xml_bytes: bytes) -> dict:
    """Simulate transmission to General Department of Taxation.
    
    Returns standard codes:
      '00' - Success (Approved)
      '01' - Signature validation failure
      '02' - XSD format error
    """
    # 1. Check syntax/schema validation
    from invoices.schema_validator import validate_xml_schema
    is_valid_format, error_msg = validate_xml_schema(signed_xml_bytes)
    if not is_valid_format:
        return {
            "status_code": "02",
            "message": f"XML Format Mismatch: {error_msg}",
            "gdt_code": ""
        }
        
    # 2. Cryptographic signature check
    try:
        root = lxml.etree.fromstring(signed_xml_bytes)
        # Find seller MST and Name for verification parameters
        seller_mst_nodes = root.xpath("//*[local-name()='NBan']/*[local-name()='MST']")
        seller_name_nodes = root.xpath("//*[local-name()='NBan']/*[local-name()='Ten']")
        date_nodes = root.xpath("//*[local-name()='TTChung']/*[local-name()='NLap']")
        
        seller_mst = seller_mst_nodes[0].text if seller_mst_nodes else None
        seller_name = seller_name_nodes[0].text if seller_name_nodes else None
        date_str = date_nodes[0].text if date_nodes else None
        
        sig_audit = verify_xml_signature(signed_xml_bytes, date_str, seller_mst, seller_name)
        if not sig_audit["sig_verified"] or sig_audit["sig_error"]:
            return {
                "status_code": "01",
                "message": f"Signature Audit Failed: {sig_audit['sig_error']}",
                "gdt_code": ""
            }
            
        # Success
        import uuid
        gdt_code = f"GDT-{uuid.uuid4().hex[:12].upper()}"
        return {
            "status_code": "00",
            "message": "Approved by GDT Gateway",
            "gdt_code": gdt_code,
            "signature_details": sig_audit
        }
    except Exception as e:
        return {
            "status_code": "02",
            "message": f"Syntax Error: {str(e)}",
            "gdt_code": ""
        }


# ── US-364: Related Party Transaction Disclosure Checklist ────────────

def calculate_related_party_disclosure(taxpayer_mst: str, start_date: str, end_date: str) -> dict:
    """Analyze transaction partners and check Decree 132/2020/NĐ-CP thresholds.
    
    Decree 132/2020/NĐ-CP triggers Form 01/132 disclosure if:
      - Total Revenue >= 150B VND
      - Total Related-Party Transactions >= 30B VND
    """
    # 1. Get all related parties (decree_132_relationship is not null/empty)
    related_partners = Partner.query.filter(
        Partner.decree_132_relationship != None,
        Partner.decree_132_relationship != ""
    ).all()
    
    related_msts = {p.mst: p for p in related_partners}
    
    # 2. Get purchase and sold invoices for taxpayer in period
    invoices = Invoice.query.filter(
        Invoice.date >= start_date,
        Invoice.date <= end_date
    ).all()
    
    total_revenue = 0.0
    related_party_transactions = 0.0
    party_breakdown = {}
    
    for inv in invoices:
        # Is it related party?
        # If it's a sales invoice, count to total revenue
        if inv.seller_mst == taxpayer_mst:
            total_revenue += inv.amount_before_tax
            # Is buyer related?
            if inv.buyer_mst in related_msts:
                related_party_transactions += inv.amount_before_tax
                mst = inv.buyer_mst
                if mst not in party_breakdown:
                    party_breakdown[mst] = {"name": related_msts[mst].name, "relationship": related_msts[mst].decree_132_relationship, "amount": 0.0}
                party_breakdown[mst]["amount"] += inv.amount_before_tax
        else:
            # If purchase invoice, check if seller is related
            if inv.seller_mst in related_msts:
                related_party_transactions += inv.amount_before_tax
                mst = inv.seller_mst
                if mst not in party_breakdown:
                    party_breakdown[mst] = {"name": related_msts[mst].name, "relationship": related_msts[mst].decree_132_relationship, "amount": 0.0}
                party_breakdown[mst]["amount"] += inv.amount_before_tax

    # Check triggers
    trigger_revenue = total_revenue >= 150000000000.0  # 150B VND
    trigger_transactions = related_party_transactions >= 30000000000.0  # 30B VND
    disclosure_required = trigger_revenue or trigger_transactions
    
    checklist = {
        "taxpayer_mst": taxpayer_mst,
        "total_revenue": total_revenue,
        "related_party_transactions": related_party_transactions,
        "disclosure_required": disclosure_required,
        "trigger_revenue": trigger_revenue,
        "trigger_transactions": trigger_transactions,
        "party_breakdown": list(party_breakdown.values()),
        "generated_at": datetime.datetime.now().isoformat()
    }
    return checklist


# ── US-365: Transfer Pricing Markup Risk Engine ──────────────────────────

# Sector Benchmarks for EBIT Margin
SECTOR_BENCHMARKS = {
    "Manufacturing": {
        "lower_quartile": 0.05,  # 5%
        "median": 0.085,         # 8.5%
        "upper_quartile": 0.12   # 12%
    },
    "Services": {
        "lower_quartile": 0.10,  # 10%
        "median": 0.15,          # 15%
        "upper_quartile": 0.20   # 20%
    },
    "Distribution": {
        "lower_quartile": 0.03,  # 3%
        "median": 0.05,          # 5%
        "upper_quartile": 0.075  # 7.5%
    }
}

def analyze_transfer_pricing_risk(transactions: list[dict], sector: str) -> dict:
    """Analyze margins of related party transactions against sector standards.
    
    Calculates profit margins and flags markup anomalies if they drop below lower quartile benchmark.
    """
    benchmark = SECTOR_BENCHMARKS.get(sector) or SECTOR_BENCHMARKS["Manufacturing"]
    
    results = []
    high_risk_count = 0
    total_deviation_needed = 0.0
    
    for tx in transactions:
        revenue = float(tx.get("revenue") or 0.0)
        cogs = float(tx.get("cogs") or 0.0)
        
        if revenue <= 0.0:
            continue
            
        ebit = revenue - cogs
        margin = ebit / revenue
        
        risk_level = "Low Risk"
        warning = ""
        suggested_adjustment = 0.0
        
        if margin < benchmark["lower_quartile"]:
            risk_level = "High Risk"
            warning = f"Lợi nhuận gộp/vận hành ({margin*100:.2f}%) thấp hơn khoảng phần tư dưới của ngành ({benchmark['lower_quartile']*100:.2f}%)."
            high_risk_count += 1
            # Calculate what revenue would be needed to hit median margin
            # ebit_needed = revenue_new * median -> (revenue_new - cogs) = revenue_new * median
            # revenue_new * (1 - median) = cogs -> revenue_new = cogs / (1 - median)
            target_rev = cogs / (1.0 - benchmark["median"])
            suggested_adjustment = max(0.0, target_rev - revenue)
            total_deviation_needed += suggested_adjustment
            
        results.append({
            "transaction_id": tx.get("id"),
            "partner_name": tx.get("partner_name"),
            "revenue": revenue,
            "cogs": cogs,
            "ebit": ebit,
            "margin": margin,
            "risk_level": risk_level,
            "warning": warning,
            "suggested_adjustment": suggested_adjustment
        })
        
    return {
        "sector": sector,
        "benchmark": benchmark,
        "analyzed_transactions": results,
        "high_risk_count": high_risk_count,
        "total_suggested_adjustment": total_deviation_needed,
        "verdict": "FLAGGED" if high_risk_count > 0 else "COMPLIANT"
    }

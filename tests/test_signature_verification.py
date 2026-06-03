import base64
import io
import lxml.etree
from datetime import datetime, timedelta, timezone
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.serialization import Encoding

from invoices.signature_verifier import (
    clean_company_name,
    are_company_names_similar,
    verify_xml_signature
)

def generate_test_cert(cn: str, org: str | None = None, mst: str | None = None, days_valid: int = 365):
    """Helper to generate a self-signed certificate for testing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    subject_parts = [
        x509.NameAttribute(NameOID.COMMON_NAME, cn),
    ]
    if org:
        subject_parts.append(x509.NameAttribute(NameOID.ORGANIZATION_NAME, org))
    if mst:
        subject_parts.append(x509.NameAttribute(NameOID.SERIAL_NUMBER, f"MST:{mst}"))
        
    subject = x509.Name(subject_parts)
    issuer = subject
    
    now = datetime.now(timezone.utc)
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        now - timedelta(days=1)
    ).not_valid_after(
        now + timedelta(days=days_valid)
    ).sign(private_key, hashes.SHA256())
    
    return private_key, cert

def test_company_name_cleaning():
    """Test normalization and cleaning of Vietnamese company names."""
    assert clean_company_name("Công ty TNHH Giải pháp Tin học A") == "giaiphaptinhoca"
    assert clean_company_name("CÔNG TY CỔ PHẦN MISA") == "misa"
    assert clean_company_name("Dịch Vụ Thương Mại ABC 1 Thành Viên") == "abc"
    assert clean_company_name("") == ""

def test_company_name_similarity():
    """Test token-based and substring similarity comparison."""
    assert are_company_names_similar("Công ty TNHH Giải pháp MISA", "Giải Pháp MISA") is True
    assert are_company_names_similar("Công ty Cổ phần viễn thông FPT", "FPT Telecom") is True
    assert are_company_names_similar("Cổ phần công nghệ mới Sao Việt", "Sao Việt Tech") is True
    assert are_company_names_similar("Công ty Hoàng Gia", "Công ty Nguyễn Lê") is False

def test_verify_xml_signature_valid_flow():
    """Test cryptographic signature verification using a generated certificate."""
    seller_name = "Công ty TNHH Đầu tư MISA"
    seller_mst = "0101234567"
    
    # Generate certificate issued by MISA CA (trusted CA list)
    private_key, cert = generate_test_cert(
        cn="MISA-CA",
        org="Công ty Cổ phần MISA",
        mst=seller_mst
    )
    
    cert_b64 = base64.b64encode(cert.public_bytes(Encoding.DER)).decode("utf-8")
    
    # Create template
    xml_template = f"""<HDon>
      <DLHDon>
        <NBan>
          <Ten>{seller_name}</Ten>
          <MST>{seller_mst}</MST>
        </NBan>
      </DLHDon>
      <Signature>
        <SignedInfo>
          <SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
        </SignedInfo>
        <SignatureValue></SignatureValue>
        <KeyInfo>
          <X509Data>
            <X509Certificate>{cert_b64}</X509Certificate>
          </X509Data>
        </KeyInfo>
      </Signature>
    </HDon>"""
    
    root = lxml.etree.fromstring(xml_template)
    sig_elem = root.xpath("//*[local-name()='Signature']")[0]
    signed_info_elem = sig_elem.xpath(".//*[local-name()='SignedInfo']")[0]
    c14n_data = lxml.etree.tostring(signed_info_elem, method="c14n")
    
    # Sign canonicalized SignedInfo
    signature = private_key.sign(
        c14n_data,
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    
    sig_b64 = base64.b64encode(signature).decode("utf-8")
    sig_val_elem = sig_elem.xpath(".//*[local-name()='SignatureValue']")[0]
    sig_val_elem.text = sig_b64
    
    xml_bytes = lxml.etree.tostring(root)
    
    res = verify_xml_signature(
        xml_bytes,
        invoice_date_str=datetime.now().strftime("%Y-%m-%d"),
        seller_mst=seller_mst,
        seller_name=seller_name
    )
    
    assert res["sig_verified"] is True
    assert res["sig_ca_trusted"] is True
    assert res["sig_name_match"] is True
    assert res["sig_mst"] == seller_mst
    assert not res["sig_error"]

def test_verify_xml_signature_untrusted_ca():
    """Test warning when signature is issued by an untrusted CA."""
    seller_name = "Công ty TNHH Đầu tư MISA"
    seller_mst = "0101234567"
    
    # Generate certificate issued by "Fake-CA" (not in trusted CA list)
    private_key, cert = generate_test_cert(
        cn="Fake-CA",
        org="Công ty TNHH Đầu tư MISA",
        mst=seller_mst
    )
    
    cert_b64 = base64.b64encode(cert.public_bytes(Encoding.DER)).decode("utf-8")
    
    xml_template = f"""<HDon>
      <Signature>
        <SignedInfo>
          <SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
        </SignedInfo>
        <SignatureValue></SignatureValue>
        <KeyInfo>
          <X509Data>
            <X509Certificate>{cert_b64}</X509Certificate>
          </X509Data>
        </KeyInfo>
      </Signature>
    </HDon>"""
    
    root = lxml.etree.fromstring(xml_template)
    sig_elem = root.xpath("//*[local-name()='Signature']")[0]
    signed_info_elem = sig_elem.xpath(".//*[local-name()='SignedInfo']")[0]
    c14n_data = lxml.etree.tostring(signed_info_elem, method="c14n")
    
    signature = private_key.sign(
        c14n_data,
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    
    sig_b64 = base64.b64encode(signature).decode("utf-8")
    sig_val_elem = sig_elem.xpath(".//*[local-name()='SignatureValue']")[0]
    sig_val_elem.text = sig_b64
    
    xml_bytes = lxml.etree.tostring(root)
    
    res = verify_xml_signature(
        xml_bytes,
        seller_name=seller_name
    )
    
    assert res["sig_verified"] is True
    assert res["sig_ca_trusted"] is False
    assert "chưa được cấp phép" in res["sig_error"]

def test_verify_xml_signature_name_mismatch():
    """Test warning when certificate subject does not match seller name."""
    seller_name = "Công ty TNHH Đầu tư MISA"
    cert_org = "Công ty TNHH May Mặc ABC"
    seller_mst = "0101234567"
    
    private_key, cert = generate_test_cert(
        cn=cert_org,
        org=cert_org,
        mst=seller_mst
    )
    
    cert_b64 = base64.b64encode(cert.public_bytes(Encoding.DER)).decode("utf-8")
    
    xml_template = f"""<HDon>
      <Signature>
        <SignedInfo>
          <SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
        </SignedInfo>
        <SignatureValue></SignatureValue>
        <KeyInfo>
          <X509Data>
            <X509Certificate>{cert_b64}</X509Certificate>
          </X509Data>
        </KeyInfo>
      </Signature>
    </HDon>"""
    
    root = lxml.etree.fromstring(xml_template)
    sig_elem = root.xpath("//*[local-name()='Signature']")[0]
    signed_info_elem = sig_elem.xpath(".//*[local-name()='SignedInfo']")[0]
    c14n_data = lxml.etree.tostring(signed_info_elem, method="c14n")
    
    signature = private_key.sign(
        c14n_data,
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    
    sig_b64 = base64.b64encode(signature).decode("utf-8")
    sig_val_elem = sig_elem.xpath(".//*[local-name()='SignatureValue']")[0]
    sig_val_elem.text = sig_b64
    
    xml_bytes = lxml.etree.tostring(root)
    
    res = verify_xml_signature(
        xml_bytes,
        seller_name=seller_name
    )
    
    assert res["sig_verified"] is True
    assert res["sig_name_match"] is False
    assert "không khớp với tên người bán" in res["sig_error"]


def test_verify_xml_signature_exclusive_c14n():
    """Test cryptographic signature verification with exclusive C14N and PrefixList."""
    seller_name = "Công ty TNHH Đầu tư MISA"
    seller_mst = "0101234567"
    
    private_key, cert = generate_test_cert(
        cn="MISA-CA",
        org="Công ty Cổ phần MISA",
        mst=seller_mst
    )
    
    cert_b64 = base64.b64encode(cert.public_bytes(Encoding.DER)).decode("utf-8")
    
    xml_template = f"""<HDon xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
      <DLHDon>
        <NBan>
          <Ten>{seller_name}</Ten>
          <MST>{seller_mst}</MST>
        </NBan>
      </DLHDon>
      <ds:Signature>
        <ds:SignedInfo>
          <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
            <InclusiveNamespaces PrefixList="ds" xmlns="http://www.w3.org/2001/10/xml-exc-c14n#"/>
          </ds:CanonicalizationMethod>
          <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
        </ds:SignedInfo>
        <ds:SignatureValue></ds:SignatureValue>
        <ds:KeyInfo>
          <ds:X509Data>
            <ds:X509Certificate>{cert_b64}</ds:X509Certificate>
          </ds:X509Data>
        </ds:KeyInfo>
      </ds:Signature>
    </HDon>"""
    
    root = lxml.etree.fromstring(xml_template)
    sig_elem = root.xpath("//*[local-name()='Signature']")[0]
    signed_info_elem = sig_elem.xpath(".//*[local-name()='SignedInfo']")[0]
    
    # Extract details for signing canonicalization
    c14n_data = lxml.etree.tostring(
        signed_info_elem,
        method="c14n",
        exclusive=True,
        inclusive_ns_prefixes=["ds"]
    )
    
    signature = private_key.sign(
        c14n_data,
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    
    sig_b64 = base64.b64encode(signature).decode("utf-8")
    sig_val_elem = sig_elem.xpath(".//*[local-name()='SignatureValue']")[0]
    sig_val_elem.text = sig_b64
    
    xml_bytes = lxml.etree.tostring(root)
    
    res = verify_xml_signature(
        xml_bytes,
        invoice_date_str=datetime.now().strftime("%Y-%m-%d"),
        seller_mst=seller_mst,
        seller_name=seller_name
    )
    
    assert res["sig_verified"] is True
    assert res["sig_ca_trusted"] is True
    assert res["sig_name_match"] is True
    assert not res["sig_error"]


def test_verify_xml_signature_node_tampering():
    """Test cryptographic node-level tampering detection."""
    seller_name = "Công ty TNHH Đầu tư MISA"
    seller_mst = "0101234567"
    
    private_key, cert = generate_test_cert(
        cn="MISA-CA",
        org="Công ty Cổ phần MISA",
        mst=seller_mst
    )
    
    cert_b64 = base64.b64encode(cert.public_bytes(Encoding.DER)).decode("utf-8")
    
    # 1. First, build canonical content for the referenced node to compute its valid digest
    ref_node_content = b'<Data Id="invoice-body"><Value>1000000</Value></Data>'
    ref_node_hashed = hashes.Hash(hashes.SHA256())
    ref_node_hashed.update(ref_node_content)
    ref_node_digest = base64.b64encode(ref_node_hashed.finalize()).decode("utf-8").strip()

    xml_template = f"""<HDon>
      <Data Id="invoice-body"><Value>1000000</Value></Data>
      <Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
        <SignedInfo>
          <CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
          <SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
          <Reference URI="#invoice-body">
            <Transforms>
              <Transform Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
            </Transforms>
            <DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
            <DigestValue>{ref_node_digest}</DigestValue>
          </Reference>
        </SignedInfo>
        <SignatureValue></SignatureValue>
        <KeyInfo>
          <X509Data>
            <X509Certificate>{cert_b64}</X509Certificate>
          </X509Data>
        </KeyInfo>
      </Signature>
    </HDon>"""
    
    root = lxml.etree.fromstring(xml_template.encode("utf-8"))
    sig_elem = root.xpath("//*[local-name()='Signature']")[0]
    signed_info_elem = sig_elem.xpath(".//*[local-name()='SignedInfo']")[0]
    c14n_data = lxml.etree.tostring(signed_info_elem, method="c14n")
    
    # Sign canonicalized SignedInfo
    signature = private_key.sign(
        c14n_data,
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    
    sig_b64 = base64.b64encode(signature).decode("utf-8")
    sig_val_elem = sig_elem.xpath(".//*[local-name()='SignatureValue']")[0]
    sig_val_elem.text = sig_b64
    
    xml_bytes_valid = lxml.etree.tostring(root)
    
    # Verify valid XML
    res_valid = verify_xml_signature(
        xml_bytes_valid,
        invoice_date_str=datetime.now().strftime("%Y-%m-%d"),
        seller_mst=seller_mst,
        seller_name=seller_name
    )
    assert res_valid["sig_verified"] is True
    assert len(res_valid["sig_tampered_nodes"]) == 0

    # 2. Alter the node value to simulate tampering
    root_tampered = lxml.etree.fromstring(xml_bytes_valid)
    data_value = root_tampered.find(".//Value")
    data_value.text = "9999999"  # Tampered!
    
    xml_bytes_tampered = lxml.etree.tostring(root_tampered)
    
    res_tampered = verify_xml_signature(
        xml_bytes_tampered,
        invoice_date_str=datetime.now().strftime("%Y-%m-%d"),
        seller_mst=seller_mst,
        seller_name=seller_name
    )
    assert "#invoice-body" in res_tampered["sig_tampered_nodes"]


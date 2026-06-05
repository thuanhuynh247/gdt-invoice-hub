import os
import sys
from datetime import datetime

# Add the project root to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from extensions import db
from invoices.models import Invoice, LineItem, TaxpayerProfile, BankTransaction, CustomsDeclaration

def seed_data():
    app = create_app()
    with app.app_context():
        print("Cleaning up old invoices, profiles, bank transactions, and customs declarations...")
        # Clear existing entries for testing MST to avoid unique constraints/key collisions
        target_mst = "0108234857"
        
        # Delete dependencies first
        invoices = Invoice.query.filter_by(taxpayer_mst=target_mst).all()
        invoice_ids = [inv.id for inv in invoices]
        
        if invoice_ids:
            LineItem.query.filter(LineItem.invoice_id.in_(invoice_ids)).delete(synchronize_session=False)
            db.session.commit()
            
        Invoice.query.filter_by(taxpayer_mst=target_mst).delete(synchronize_session=False)
        BankTransaction.query.filter_by(taxpayer_mst=target_mst).delete(synchronize_session=False)
        CustomsDeclaration.query.filter_by(taxpayer_mst=target_mst).delete(synchronize_session=False)
        
        # Ensure target taxpayer profile exists
        profile = TaxpayerProfile.query.get(target_mst)
        if not profile:
            profile = TaxpayerProfile(
                mst=target_mst,
                company_name="UAT Test Company",
                gdt_username="uat_test_co",
                gdt_password_encrypted="pbkdf2:sha256:...",
                is_active=True,
                created_at=datetime.now().isoformat()
            )
            db.session.add(profile)
            print(f"Created TaxpayerProfile for {target_mst}")
        else:
            profile.company_name = "UAT Test Company"
            print(f"TaxpayerProfile for {target_mst} already exists, updating name.")

        db.session.commit()

        # 1. Seed Sales (Domestic & Export)
        # Standard domestic sale: 1B VND, VAT 10% (100M VND)
        sale_domestic = Invoice(
            id="SALE-DOM-01",
            filename="sale_dom_1.xml",
            invoice_type="sale",
            template_code="1/001",
            symbol="1C26TBA",
            number="0001001",
            date="2026-05-10",
            currency="VND",
            seller_mst=target_mst,
            seller_name="UAT Test Company",
            buyer_mst="0311223344",
            buyer_name="KHACH HANG DOMESTIC",
            amount_before_tax=1000000000.0,
            tax_amount=100000000.0,
            total_amount=1100000000.0,
            has_signature=True,
            taxpayer_mst=target_mst,
            imported_at=datetime.now().isoformat()
        )
        
        # Export sale: 200M VND, VAT 0% (0M VND)
        sale_export = Invoice(
            id="SALE-EXP-01",
            filename="sale_exp_1.xml",
            invoice_type="sale",
            template_code="1/001",
            symbol="1C26TBB",
            number="0001002",
            date="2026-05-15",
            currency="VND",
            seller_mst=target_mst,
            seller_name="UAT Test Company",
            buyer_mst="099888777",
            buyer_name="OVERSEAS BUYER LTD",
            amount_before_tax=200000000.0,
            tax_amount=0.0,
            total_amount=200000000.0,
            has_signature=True,
            taxpayer_mst=target_mst,
            imported_at=datetime.now().isoformat()
        )
        db.session.add_all([sale_domestic, sale_export])
        db.session.commit()

        # Add Line Items for Sales
        item_dom = LineItem(
            invoice_id="SALE-DOM-01",
            item_name="Dich vu tu van phan mem",
            quantity=1.0,
            unit_price=1000000000.0,
            amount_before_tax=1000000000.0,
            tax_rate="10%",
            tax_amount=100000000.0
        )
        item_exp = LineItem(
            invoice_id="SALE-EXP-01",
            item_name="Phan mem xuat khau",
            quantity=1.0,
            unit_price=200000000.0,
            amount_before_tax=200000000.0,
            tax_rate="0%",
            tax_amount=0.0
        )
        db.session.add_all([item_dom, item_exp])
        db.session.commit()

        # 2. Seed Purchases (VAT Input)
        # Purchase 1: Valid Input (320M VAT) -> Eligible
        pur_valid = Invoice(
            id="PUR-VAL-01",
            filename="pur_val_1.xml",
            invoice_type="purchase",
            template_code="1/001",
            symbol="2C26TBA",
            number="0002001",
            date="2026-05-12",
            currency="VND",
            seller_mst="0104444333",
            seller_name="NHA CUNG CAP XANG DAU",
            buyer_mst=target_mst,
            buyer_name="UAT Test Company",
            amount_before_tax=3200000000.0,
            tax_amount=320000000.0,
            total_amount=3520000000.0,
            has_signature=True,
            t_score=85,
            payment_method="Chuyển khoản ngân hàng",
            taxpayer_mst=target_mst,
            imported_at=datetime.now().isoformat()
        )
        
        # Purchase 2: Ineligible due to low T-Score (50M VAT)
        pur_low_t = Invoice(
            id="PUR-LOW-T-01",
            filename="pur_low_t.xml",
            invoice_type="purchase",
            template_code="1/001",
            symbol="2C26TBB",
            number="0002002",
            date="2026-05-14",
            currency="VND",
            seller_mst="010555666",
            seller_name="CONG TY MA",
            buyer_mst=target_mst,
            buyer_name="UAT Test Company",
            amount_before_tax=500000000.0,
            tax_amount=50000000.0,
            total_amount=550000000.0,
            has_signature=True,
            t_score=30,
            payment_method="Chuyển khoản",
            taxpayer_mst=target_mst,
            imported_at=datetime.now().isoformat()
        )

        # Purchase 3: Ineligible due to cash payment of high value invoice (30M VAT)
        pur_cash = Invoice(
            id="PUR-CASH-01",
            filename="pur_cash.xml",
            invoice_type="purchase",
            template_code="1/001",
            symbol="2C26TBC",
            number="0002003",
            date="2026-05-16",
            currency="VND",
            seller_mst="010777888",
            seller_name="CUA HANG BAN BUON",
            buyer_mst=target_mst,
            buyer_name="UAT Test Company",
            amount_before_tax=300000000.0,
            tax_amount=30000000.0,
            total_amount=330000000.0,
            has_signature=True,
            t_score=90,
            payment_method="Tiền mặt",
            taxpayer_mst=target_mst,
            imported_at=datetime.now().isoformat()
        )

        # Purchase 4: Ineligible due to missing signature (10M VAT)
        pur_no_sig = Invoice(
            id="PUR-NOSIG-01",
            filename="pur_nosig.xml",
            invoice_type="purchase",
            template_code="1/001",
            symbol="2C26TBD",
            number="0002004",
            date="2026-05-18",
            currency="VND",
            seller_mst="010888999",
            seller_name="CÔNG TY THƯƠNG MẠI",
            buyer_mst=target_mst,
            buyer_name="UAT Test Company",
            amount_before_tax=100000000.0,
            tax_amount=10000000.0,
            total_amount=110000000.0,
            has_signature=False,
            t_score=95,
            payment_method="Chuyển khoản",
            taxpayer_mst=target_mst,
            imported_at=datetime.now().isoformat()
        )

        db.session.add_all([pur_valid, pur_low_t, pur_cash, pur_no_sig])
        db.session.commit()

        # Add Purchase Line Items
        line_valid = LineItem(
            invoice_id="PUR-VAL-01",
            item_name="Xang RON 95 thuong hang",
            quantity=160000.0,
            unit_price=20000.0,
            amount_before_tax=3200000000.0,
            tax_rate="10%",
            tax_amount=320000000.0
        )
        line_low_t = LineItem(
            invoice_id="PUR-LOW-T-01",
            item_name="Dich vu tiep thi gia tạo",
            quantity=1.0,
            unit_price=500000000.0,
            amount_before_tax=500000000.0,
            tax_rate="10%",
            tax_amount=50000000.0
        )
        line_cash = LineItem(
            invoice_id="PUR-CASH-01",
            item_name="Thiet bi may tinh van phong",
            quantity=10.0,
            unit_price=30000000.0,
            amount_before_tax=300000000.0,
            tax_rate="10%",
            tax_amount=30000000.0
        )
        line_no_sig = LineItem(
            invoice_id="PUR-NOSIG-01",
            item_name="Nguyen lieu san xuat",
            quantity=1.0,
            unit_price=100000000.0,
            amount_before_tax=100000000.0,
            tax_rate="10%",
            tax_amount=10000000.0
        )
        db.session.add_all([line_valid, line_low_t, line_cash, line_no_sig])
        db.session.commit()

        # 3. Seed matching bank transaction for PUR-VAL-01
        tx_match = BankTransaction(
            id="TX-VAL-01",
            taxpayer_mst=target_mst,
            bank_name="Vietcombank",
            transaction_date="2026-05-13",
            description="THANH TOAN TIEN MUA XANG DAU THEO HD 0002001",
            amount=-3520000000.0,
            status="matched",
            matched_invoice_id="PUR-VAL-01",
            imported_at=datetime.now().isoformat()
        )
        db.session.add(tx_match)
        db.session.commit()

        # 4. Seed Customs Declaration for SALE-EXP-01
        cd_match = CustomsDeclaration(
            declaration_number="1020304050",
            declaration_date="2026-05-15",
            taxpayer_mst=target_mst,
            customs_value_vnd=200000000.0,
            import_duty_vnd=0.0,
            import_vat_vnd=0.0,
            exchange_rate=1.0,
            currency="VND",
            hs_codes_json='["8523.49.19"]',
            matching_invoice_id="SALE-EXP-01",
            status="matched"
        )
        db.session.add(cd_match)
        db.session.commit()

        # Invalidate cache
        try:
            from invoices.stats_cache import invalidate_stats_cache
            invalidate_stats_cache(target_mst)
            invalidate_stats_cache(None)
        except Exception:
            pass

        print("Done seeding VAT Refund UAT data successfully!")

if __name__ == "__main__":
    seed_data()

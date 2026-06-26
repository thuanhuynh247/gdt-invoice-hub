import sqlite3

def register():
    conn = sqlite3.connect("harness.db")
    cur = conn.cursor()
    
    # Register US-940
    cur.execute("""
        INSERT OR REPLACE INTO story (
            id, title, risk_lane, status, contract_doc, notes
        ) VALUES (
            'US-940', 
            'V78 XML Invoice Validation and Benford Law Audit Engine', 
            'normal', 
            'implemented', 
            'docs/stories/US-940-invoice-validation.md', 
            'Xay dung he thong kiem tra tinh hop le cua hoa don theo Nghi dinh 125, Luat Quan ly Thue va phan tich tan suat chu so dau tien (Luat Benford) de phat hien bat thuong.'
        )
    """)
    
    # Register US-950
    cur.execute("""
        INSERT OR REPLACE INTO story (
            id, title, risk_lane, status, contract_doc, notes
        ) VALUES (
            'US-950', 
            'PixelRAG AI Tax Advisor Chatbot and Document Ingestion Engine', 
            'normal', 
            'implemented', 
            'docs/stories/US-950-tax-advisor.md', 
            'Xay dung tro ly ao co van thue AI, tich hop cong nghe PixelRAG trich xuat anh trang tai lieu luat thue thuc te ho tro giai dap phap ly thue GTGT.'
        )
    """)
    
    conn.commit()
    conn.close()
    print("Stories US-940 and US-950 successfully registered in harness.db")

if __name__ == "__main__":
    register()

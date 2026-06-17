import sqlite3

def register():
    conn = sqlite3.connect("harness.db")
    cur = conn.cursor()
    
    stories = [
        (
            'US-490',
            'CEO Executive KPI Dashboard & Financial Health Score',
            'normal',
            'planned',
            'docs/stories/US-490-ceo-dashboard.md',
            'Centralize Revenue, Expense, Tax Liability, Cash Flow, and compliance metrics into a single glassmorphic CEO command center with an overall Financial Health Score (0-100).'
        ),
        (
            'US-491',
            'Multi-Year Tax Projection Engine & Optimization Simulator',
            'normal',
            'planned',
            'docs/stories/US-491-tax-projection-engine.md',
            'Forecast VAT, CIT, PIT, and FCT obligations 3-5 years ahead using historical invoice data, trend regression, and user-defined growth assumptions.'
        ),
        (
            'US-492',
            'Comprehensive Tax Filing Calendar & Compliance Tracker',
            'normal',
            'planned',
            'docs/stories/US-492-tax-filing-calendar.md',
            'Provide a calendar-view of all Vietnamese tax filing deadlines per Luật Quản lý Thuế 2019 and Thông tư 80/2021, track filed vs pending status.'
        ),
        (
            'US-493',
            'Fixed Asset Registry & Depreciation Engine (TT45/2013)',
            'normal',
            'planned',
            'docs/stories/US-493-fixed-asset-registry.md',
            'Register fixed assets with acquisition date, original cost, useful life, and depreciation method. Compute monthly/annual depreciation per TT 45/2013.'
        ),
        (
            'US-494',
            'AI Invoice-to-Asset Linker & CIT Depreciation Validator',
            'normal',
            'planned',
            'docs/stories/US-494-ai-asset-linker.md',
            'Auto-detect purchase invoices ≥ 30M VND likely representing fixed assets, suggest asset creation, and validate compliance.'
        ),
        (
            'US-495',
            'End-to-End V37 Financial Intelligence Validation Suite',
            'normal',
            'planned',
            'docs/stories/US-495-v37-test-suite.md',
            'Comprehensive regression test coverage for CEO dashboard computations, tax projection formulas, calendar logic, asset depreciation, and AI linking.'
        )
    ]
    
    for story in stories:
        cur.execute("""
            INSERT OR REPLACE INTO story (
                id, title, risk_lane, status, contract_doc, notes
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, story)
        
    conn.commit()
    conn.close()
    print("V37 stories successfully registered/updated in harness.db")

if __name__ == "__main__":
    register()

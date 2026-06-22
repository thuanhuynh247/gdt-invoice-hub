import sqlite3

def main():
    conn = sqlite3.connect('harness.db')
    cur = conn.cursor()
    cur.execute("SELECT id, title, risk_lane, contract_doc, status, notes, unit_proof, integration_proof, e2e_proof, platform_proof, evidence FROM story WHERE status != 'completed'")
    for row in cur.fetchall():
        print("="*60)
        print(f"ID: {row[0]}")
        print(f"Title: {row[1]}")
        print(f"Status: {row[4]}")
        print(f"Risk Lane: {row[2]}")
        print(f"Proofs (Unit/Int/E2E/Plat): {row[6]}/{row[7]}/{row[8]}/{row[9]}")
        print("-"*30)
        print(f"Contract Doc:\n{row[3]}")
        print("-"*30)
        print(f"Notes:\n{row[5]}")
        print("-"*30)
        print(f"Evidence:\n{row[10]}")
    conn.close()

if __name__ == "__main__":
    main()

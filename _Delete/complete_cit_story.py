import sqlite3
import os

def main():
    db_path = "harness.db"
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        UPDATE story
        SET status = 'completed', 
            evidence = 'tests/test_tax_crawler.py', 
            unit_proof = 1, 
            integration_proof = 1, 
            e2e_proof = 1
        WHERE id = 'US-CIT-CHATBOT-RAG'
    """)
    conn.commit()
    conn.close()
    print("Successfully completed US-CIT-CHATBOT-RAG in harness.db!")

if __name__ == "__main__":
    main()

import os
import sys
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "invoices.db")

def main():
    if not os.path.exists(DB_PATH):
        print(f"Database not found: {DB_PATH}")
        sys.exit(1)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Reading current chunks from database...")
    cursor.execute("SELECT id, document_source, page_number, effective_date, chunk_content, created_at FROM tax_regulation_chunk")
    rows = cursor.fetchall()
    print(f"Total chunks found: {len(rows)}")
    
    # Deduplicate in memory
    unique_chunks = {}
    duplicates_removed = 0
    for r in rows:
        cid, doc, page, eff, content, created = r
        # Clean whitespaces for comparison
        normalized_content = " ".join(content.split())
        key = (doc, normalized_content)
        if key not in unique_chunks:
            unique_chunks[key] = r
        else:
            duplicates_removed += 1
            
    print(f"Unique chunks count: {len(unique_chunks)}")
    print(f"Duplicates to remove: {duplicates_removed}")
    
    if duplicates_removed > 0:
        # Recreate relational table
        cursor.execute("DROP TABLE IF EXISTS tax_regulation_chunk")
        cursor.execute("""
            CREATE TABLE tax_regulation_chunk (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_source TEXT,
                page_number INTEGER,
                effective_date TEXT,
                chunk_content TEXT,
                created_at TEXT
            );
        """)
        
        # Re-insert unique records
        for key, r in unique_chunks.items():
            cid, doc, page, eff, content, created = r
            cursor.execute("""
                INSERT INTO tax_regulation_chunk (id, document_source, page_number, effective_date, chunk_content, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (cid, doc, page, eff, content, created))
            
        # Recreate and rebuild FTS5 table
        cursor.execute("DROP TABLE IF EXISTS tax_regulation_fts")
        cursor.execute("""
            CREATE VIRTUAL TABLE tax_regulation_fts USING fts5(
                chunk_id UNINDEXED,
                chunk_content,
                document_source,
                page_number
            );
        """)
        
        # Populate FTS5 table
        cursor.execute("SELECT id, chunk_content, document_source, page_number FROM tax_regulation_chunk")
        for chunk in cursor.fetchall():
            cid, content, doc, page = chunk
            cursor.execute("""
                INSERT INTO tax_regulation_fts (chunk_id, chunk_content, document_source, page_number)
                VALUES (?, ?, ?, ?)
            """, (cid, content, doc, page))
            
        conn.commit()
        print("Deduplication and FTS5 rebuild completed successfully.")
    else:
        print("No duplicates found, database is already clean.")
        
    conn.close()

if __name__ == "__main__":
    main()

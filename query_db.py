import sqlite3

def main():
    conn = sqlite3.connect('harness.db')
    cursor = conn.cursor()
    
    # List all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cursor.fetchall()]
    print("Tables:", tables)
    
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"\nTable: {table}, Columns: {columns}")
        
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"Row count: {count}")
        
        # Print first 2 rows
        cursor.execute(f"SELECT * FROM {table} LIMIT 2")
        rows = cursor.fetchall()
        for r in rows:
            print("  Row:", r)
            
    cursor.close()
    conn.close()

if __name__ == '__main__':
    main()

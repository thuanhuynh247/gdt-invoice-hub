import sqlite3

def main():
    conn = sqlite3.connect('harness.db')
    cursor = conn.cursor()
    
    # Query stories related to IFRS, environmental, v43 or v53
    cursor.execute("SELECT id, title, status, evidence, created_at FROM story WHERE id LIKE '%43%' OR id LIKE '%53%' OR title LIKE '%43%' OR title LIKE '%53%' OR title LIKE '%IFRS%' OR title LIKE '%Environmental%' ORDER BY id ASC")
    rows = cursor.fetchall()
    print("Filtered stories in DB:")
    for r in rows:
        print(f"ID: {r[0]} | Title: {r[1]} | Status: {r[2]} | Evidence: {r[3]} | Created: {r[4]}")
        
    cursor.close()
    conn.close()

if __name__ == '__main__':
    main()

import sqlite3

def main():
    conn = sqlite3.connect('harness.db')
    cursor = conn.cursor()
    
    # Query stories sorted by id or created_at
    cursor.execute("SELECT id, title, risk_lane, status, evidence, created_at FROM story ORDER BY id DESC LIMIT 30")
    rows = cursor.fetchall()
    print("Latest 30 stories:")
    for r in rows:
        print(f"ID: {r[0]} | Title: {r[1]} | Status: {r[3]} | Evidence: {r[4]} | Created: {r[5]}")
        
    cursor.close()
    conn.close()

if __name__ == '__main__':
    main()

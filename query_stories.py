import sqlite3

def main():
    conn = sqlite3.connect('harness.db')
    cursor = conn.cursor()
    
    # Query stories sorted by id
    cursor.execute("SELECT id, title, status, evidence, created_at FROM story WHERE id LIKE 'US-7%' OR id LIKE 'US-8%' OR id LIKE 'US-9%' ORDER BY id ASC")
    rows = cursor.fetchall()
    print("All US-7xx, US-8xx, and US-9xx stories in DB:")
    for r in rows:
        print(f"ID: {r[0]} | Title: {r[1]} | Status: {r[2]} | Evidence: {r[3]} | Created: {r[4]}")
        
    cursor.close()
    conn.close()

if __name__ == '__main__':
    main()

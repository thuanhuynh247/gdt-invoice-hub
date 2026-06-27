import sqlite3

def main():
    conn = sqlite3.connect('harness.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, status FROM story ORDER BY id DESC LIMIT 50")
    rows = cursor.fetchall()
    print("Latest 50 stories in harness.db:")
    for r in rows:
        print(f"ID: {r[0]} | Title: {r[1]} | Status: {r[2]}")
    cursor.close()
    conn.close()

if __name__ == '__main__':
    main()

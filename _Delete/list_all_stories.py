import sqlite3

def main():
    conn = sqlite3.connect('harness.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, status FROM story ORDER BY id ASC")
    rows = cursor.fetchall()
    print("All stories:")
    for r in rows:
        print(f"ID: {r[0]} | Title: {r[1]} | Status: {r[2]}")
    cursor.close()
    conn.close()

if __name__ == '__main__':
    main()

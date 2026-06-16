import sqlite3

def main():
    conn = sqlite3.connect('harness.db')
    cur = conn.cursor()
    cur.execute("SELECT status, count(*) FROM story GROUP BY status")
    print("Story status counts:")
    for row in cur.fetchall():
        print(f"Status: {row[0]}, Count: {row[1]}")
    
    cur.execute("SELECT id, title, status FROM story WHERE status != 'completed'")
    print("\nStories not 'completed':")
    for row in cur.fetchall():
        print(f"{row[0]} | {row[1]} | {row[2]}")
        
    conn.close()

if __name__ == "__main__":
    main()

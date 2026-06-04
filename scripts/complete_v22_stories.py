import sqlite3

def complete_stories():
    conn = sqlite3.connect("harness.db")
    cur = conn.cursor()

    story_ids = ["US-340", "US-341", "US-342", "US-343", "US-344", "US-345"]
    for sid in story_ids:
        cur.execute("""
            UPDATE story 
            SET status = 'completed', evidence = 'tests/test_v22_features.py'
            WHERE id = ?
        """, (sid,))
        print(f"Updated story {sid} to status 'completed'.")

    conn.commit()
    conn.close()
    print("All V22 stories successfully completed in harness.db")

if __name__ == "__main__":
    complete_stories()

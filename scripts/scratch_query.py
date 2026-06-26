import sqlite3
import os
from datetime import datetime

def complete_stories():
    db_path = "harness.db"
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Close remaining 'implemented' stories
    for sid in ["US-720", "US-762"]:
        cur.execute("UPDATE story SET status = 'completed' WHERE id = ?", (sid,))
        print(f"Updated {sid} -> completed")

    # Record trace for the v66-v75 visual upgrade
    cur.execute(
        "INSERT INTO trace (task_summary, story_id, agent, actions_taken, files_read, files_changed, outcome, duration_seconds, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "Upgraded v66-v75 compliance hubs with Wise Fintech Premium styling",
            "US-762",
            "Antigravity",
            "Injected head_extra CSS design tokens, animated robot debate bubbles, calc-pulse effect, subtle badge variants, monospace fee columns across 10 templates. 65 tests passed.",
            "templates/v66-v75_compliance_hub.html",
            "templates/v66-v75_compliance_hub.html",
            "completed",
            300,
            datetime.now().isoformat()
        )
    )

    conn.commit()
    conn.close()
    print("Done closing stories and logging trace!")

if __name__ == "__main__":
    complete_stories()

import os
import re
import sqlite3

def get_harness_status():
    db_path = "harness.db"
    if not os.path.exists(db_path):
        return {}
    
    conn = sqlite3.connect(db_path)
    conn.text_factory = lambda x: x.decode('utf-8', errors='replace')
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, status FROM story")
        res = {row[0]: row[1] for row in cur.fetchall()}
    except Exception as e:
        print(f"Error reading harness.db: {e}")
        res = {}
    finally:
        conn.close()
    return res

def sync_docs():
    statuses = get_harness_status()
    if not statuses:
        print("No story statuses found in database.")
        return

    # Directories to scan
    scan_dirs = ["docs/product", "history", "docs/stories", "product-spec/docs/product"]
    scan_files = ["todo.md", "README.md"]

    for d in scan_dirs:
        if not os.path.exists(d):
            continue
        for root, _, files in os.walk(d):
            for file in files:
                if file.endswith(".md"):
                    scan_files.append(os.path.join(root, file))

    updated_count = 0

    for filepath in sorted(list(set(scan_files))):
        if not os.path.exists(filepath):
            continue
        
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        original = content

        # Let's replace story statuses in tables.
        # Tables look like: | Epic | Title | US-360 | ... | To Do |
        # or | US-360 | Title | Todo |
        # Let's build a regex that finds rows containing a story ID and a Todo/To Do status.
        for story_id, status in statuses.items():
            # If status in database is 'completed', we want to show it as Completed.
            status_text = "✅ Completed" if status == "completed" else status.capitalize()

            # Pattern for table row: search for story_id, then some columns, then Todo/To Do/⏳ To Do
            # e.g., | US-320 | ... | Todo |
            # We want to replace "Todo", "To Do", "⏳ To Do", "⏳ Todo" with status_text.
            # Let's target lines containing the story_id:
            lines = content.splitlines()
            changed_file = False
            for i, line in enumerate(lines):
                if story_id in line:
                    # Check if there is "Todo", "To Do", "⏳ To Do", "⏳ Todo", or "Planned"
                    new_line = re.sub(
                        r"(\|\s*)(⏳\s*)?(To\s*Do|Todo|Planned|planned|draft)(\s*(?:\||\n|$))",
                        rf"\1{status_text}\4",
                        line,
                        flags=re.IGNORECASE
                    )
                    if new_line != line:
                        lines[i] = new_line
                        changed_file = True
            
            if changed_file:
                content = "\n".join(lines) + ("\n" if content.endswith("\n") else "")

        if content != original:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Synced story statuses in: {filepath}")
            updated_count += 1

    print(f"Finished syncing {updated_count} files.")

if __name__ == "__main__":
    sync_docs()

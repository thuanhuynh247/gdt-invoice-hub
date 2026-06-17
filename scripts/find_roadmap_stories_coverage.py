import os
import re
import sqlite3
import glob

def find_roadmap_coverage():
    roadmap_dir = r"d:\LearnAnyThing\Webapp XML\docs\product"
    db_path = "harness.db"
    
    # Connect to DB and fetch registered story IDs
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    db_stories = {row[0]: row[1] for row in cur.execute("SELECT id, status FROM story").fetchall()}
    conn.close()
    
    print(f"Total stories registered in DB: {len(db_stories)}")
    
    # Find all roadmap markdown files
    roadmap_files = glob.glob(os.path.join(roadmap_dir, "v*_roadmap.md"))
    
    for filepath in sorted(roadmap_files, key=lambda x: [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', x)]):
        filename = os.path.basename(filepath)
        
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
        # Extract US-XXX stories from file content
        story_ids = sorted(list(set(re.findall(r"US-\d+", content))))
        
        if not story_ids:
            continue
            
        implemented_count = 0
        missing_stories = []
        
        for sid in story_ids:
            if sid in db_stories:
                if db_stories[sid] == 'completed':
                    implemented_count += 1
                else:
                    missing_stories.append(f"{sid} ({db_stories[sid]})")
            else:
                missing_stories.append(sid)
                
        pct = (implemented_count / len(story_ids)) * 100 if story_ids else 0
        print(f"Roadmap: {filename:<25} | Found Stories: {len(story_ids):<3} | Implemented: {implemented_count:<3} ({pct:.1f}%) | Missing: {missing_stories}")

if __name__ == "__main__":
    find_roadmap_coverage()

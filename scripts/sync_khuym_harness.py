import os
import sys
import json
import sqlite3

def get_db(db_path="harness.db"):
    if not os.path.exists(db_path):
        return None
    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn
    except Exception as e:
        print(f"Warning: Failed to connect to harness.db: {e}", file=sys.stderr)
        return None

def sync_state():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    state_path = os.path.join(repo_root, ".khuym", "state.json")
    reservations_path = os.path.join(repo_root, ".khuym", "reservations.json")
    
    if not os.path.exists(state_path):
        print("Khuym state.json not found. Skipping sync.", file=sys.stderr)
        return
        
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
    except Exception as e:
        print(f"Error reading state.json: {e}", file=sys.stderr)
        return
        
    feature_slug = state.get("feature_slug", "")
    phase = state.get("phase", "")
    
    if not feature_slug:
        print("No active feature slug in state.json.", file=sys.stderr)
        return
        
    conn = get_db(os.path.join(repo_root, "harness.db"))
    if not conn:
        return
        
    try:
        # Find matching story
        # The feature_slug might be in lowercase, while story ID in harness.db is uppercase or slightly different.
        # We perform a case-insensitive search.
        cur = conn.cursor()
        cur.execute("SELECT id, status FROM story")
        stories = cur.fetchall()
        
        target_story = None
        # Try exact/token match
        normalized_slug = feature_slug.lower().replace("-", "_")
        for story_id, status in stories:
            norm_id = story_id.lower().replace("-", "_")
            if normalized_slug in norm_id or norm_id in normalized_slug:
                target_story = story_id
                break
                
        if target_story:
            # Map Khuym phase to Harness story status
            # Harness story statuses: planned, in_progress, implemented, changed, retired
            mapped_status = "planned"
            if phase in ("context", "work_shape", "phase_plan", "execution", "swarming"):
                mapped_status = "in_progress"
            elif phase in ("review", "compounding"):
                mapped_status = "implemented"
                
            cur.execute("UPDATE story SET status = ? WHERE id = ?", (mapped_status, target_story))
            conn.commit()
            print(f"[Sync] Synced Khuym feature '{feature_slug}' with Harness story '{target_story}' -> status: {mapped_status}")
        else:
            print(f"[Sync] No matching Harness story found for feature slug '{feature_slug}'.")
            
    except Exception as e:
        print(f"Error executing DB update: {e}", file=sys.stderr)
    finally:
        conn.close()

    # Sync reservations summary
    if os.path.exists(reservations_path):
        try:
            with open(reservations_path, "r", encoding="utf-8") as f:
                res_data = json.load(f)
            active_res = [r for r in res_data.get("reservations", []) if r.get("status") == "active"]
            if active_res:
                print(f"[Sync] Active File Reservations locked:")
                for r in active_res:
                    print(f"   - Agent '{r.get('agent')}' holds: {', '.join(r.get('paths', []))} (Expires: {r.get('expires_at')})")
        except Exception as e:
            print(f"Error reading reservations: {e}", file=sys.stderr)

if __name__ == "__main__":
    sync_state()

import os
import shutil
from datetime import datetime

def safe_move(src_path, dest_dir):
    """Moves a file or directory to dest_dir, avoiding collisions by adding timestamps."""
    if not os.path.exists(src_path):
        return 0, 0
    
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
        
    base_name = os.path.basename(src_path)
    dest_path = os.path.join(dest_dir, base_name)
    
    # If collision, append timestamp
    if os.path.exists(dest_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name, ext = os.path.splitext(base_name)
        if ext:
            new_name = f"{name}_{timestamp}{ext}"
        else:
            new_name = f"{name}_{timestamp}"
        dest_path = os.path.join(dest_dir, new_name)
        
    size = 0
    if os.path.isdir(src_path):
        # Calculate folder size
        for root, dirs, files in os.walk(src_path):
            for f in files:
                fp = os.path.join(root, f)
                if not os.path.islink(fp):
                    try:
                        size += os.path.getsize(fp)
                    except OSError:
                        pass
        try:
            shutil.move(src_path, dest_path)
            print(f"Moved directory {src_path} -> {dest_path}")
            return 1, size
        except Exception as e:
            print(f"Error moving directory {src_path}: {e}")
            return 0, 0
    else:
        try:
            size = os.path.getsize(src_path)
            shutil.move(src_path, dest_path)
            print(f"Moved file {src_path} -> {dest_path}")
            return 1, size
        except Exception as e:
            print(f"Error moving file {src_path}: {e}")
            return 0, 0

def run_cleanup():
    print("=" * 80)
    print("🧹 SAFE CLEANUP WORKSPACE — MOVING TO _DELETE")
    print("=" * 80)
    
    workspace_dir = "d:\\LearnAnyThing\\Webapp XML"
    delete_dir = os.path.join(workspace_dir, "_Delete")
    
    # Specific files to move
    files_to_move = [
        "job_log.txt",
        "job_log_10.txt",
        "job_log_9.txt",
        "server.log",
        "server_clean.log",
        "test_output.log",
        "test_output_utf8.log",
        "test_result.log",
        "test_verbose.log",
        "uat_smoke_test_error.log",
        "invoice_webapp_release.zip",
        "webapp-refinement.zip",
        "vietinbank_screenshot.png",
        "page1.png",
        "test.xlsx",
        "matrix.txt",
        "matrix_bold.txt",
        "harness_copy.db",
        "harness_temp.db",
        "debug_invoices.py",
        "debug_render.py",
        "query.sql",
        "query_db.py",
        "query_stories.py",
        "register_prd_fund_stories.py",
        "register_v62_v63_stories.py",
        "simulate_client.py",
        ".coverage",
    ]
    
    # Specific folders to move
    folders_to_move = [
        "tmp_pip_build",
        "temp_understand",
        "temp_ag_kit",
        ".pytest_cache",
        ".cache",
    ]
    
    # Check for wildcards like .chrome_user_data_*
    for item in os.listdir(workspace_dir):
        if item.startswith(".chrome_user_data_"):
            folders_to_move.append(item)
            
    total_moved = 0
    total_reclaimed = 0
    
    # Move files
    for f in files_to_move:
        path = os.path.join(workspace_dir, f)
        count, size = safe_move(path, delete_dir)
        total_moved += count
        total_reclaimed += size
        
    # Move folders
    for folder in folders_to_move:
        path = os.path.join(workspace_dir, folder)
        count, size = safe_move(path, delete_dir)
        total_moved += count
        total_reclaimed += size
        
    print("=" * 80)
    print(f"Reclaimed Space: {total_reclaimed / (1024*1024):.2f} MB")
    print(f"Total Items Moved: {total_moved}")
    print("=" * 80)

if __name__ == "__main__":
    run_cleanup()

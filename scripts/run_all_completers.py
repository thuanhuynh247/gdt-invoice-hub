import os
import glob
import subprocess
import sys

def main():
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    pattern = os.path.join(scripts_dir, "complete_*.py")
    completer_files = glob.glob(pattern)
    completer_files.sort()
    
    print(f"Found {len(completer_files)} completion scripts to run.")
    
    # We want to skip complete_implemented_stories.py because it only updates statuses, 
    # but we can run it first just in case.
    # We'll run all of them to make sure all statuses are updated and all traces are written.
    for fpath in completer_files:
        filename = os.path.basename(fpath)
        if filename == "run_all_completers.py":
            continue
            
        print(f"\n==================================================")
        print(f"Running: {filename}")
        print(f"==================================================")
        
        try:
            # Run the python script using the current python executable
            result = subprocess.run([sys.executable, fpath], capture_output=True, text=True, check=True)
            print(result.stdout)
            if result.stderr:
                print("Warnings/Errors:")
                print(result.stderr)
        except subprocess.CalledProcessError as e:
            print(f"Error executing {filename}:")
            print(e.stdout)
            print(e.stderr)
            
    print("\n==================================================")
    print("All completion scripts executed successfully!")
    print("==================================================")

if __name__ == "__main__":
    main()

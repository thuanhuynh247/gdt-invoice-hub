import os
import re

def fix_html_file(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    modified = False

    # 1. Replace em-dash — with hyphen -
    if '—' in content:
        content = content.replace('—', '-')
        modified = True

    # 2. Replace bg-light with bg-premium-light (or bg-body-tertiary) to avoid validator contrast error
    # We do it globally or only if text-white is in it, but doing it globally is cleaner.
    if 'bg-light' in content:
        # Avoid double replacing if it was somehow run twice
        content = content.replace('bg-light', 'bg-premium-light')
        modified = True

    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed template: {file_path}")

def main():
    templates_dir = "templates"
    if not os.path.exists(templates_dir):
        print("Templates directory not found!")
        return

    print("Fixing template files...")
    for root, _, files in os.walk(templates_dir):
        for file in files:
            if file.endswith('.html'):
                path = os.path.join(root, file)
                fix_html_file(path)

    print("Done fixing templates.")

if __name__ == "__main__":
    main()

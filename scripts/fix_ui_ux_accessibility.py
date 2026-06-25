import os
import re

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # 1. Fix icons lacking aria-hidden="true"
    # Match: <i class="...bi-..."></i> where it has no aria-hidden
    # Note: we check if it already has aria-hidden
    # The regex matches <i class="class_names"></i> where class_names contains bi-
    icon_pattern = re.compile(r'<i class="([^"]*\bbi-[^"]*)"\s*>\s*</i>')
    content = icon_pattern.sub(r'<i class="\1" aria-hidden="true"></i>', content)

    # 2. Fix placeholders containing '...'
    # Match: placeholder="text...text"
    # We replace ... with … inside placeholders
    def replace_placeholder_dots(match):
        val = match.group(1)
        val_fixed = val.replace('...', '…')
        return f'placeholder="{val_fixed}"'

    placeholder_pattern = re.compile(r'placeholder="([^"]*)"')
    content = placeholder_pattern.sub(replace_placeholder_dots, content)

    # 3. Fix general text containing '...' outside tags/scripts
    # We can do this carefully, but let's see if there are other matches.
    # In the audit script:
    # re.finditer(r'\b\.\.\.\b|(?<=\w)\.\.\.(?=\s|$)|(?<=\s)\.\.\.(?=\w|$)', content)
    # Let's replace '...' with '…' in places where it's not part of code/template.
    # A simple way to avoid template code:
    # If the '...' is followed by ' %}' or ' }}', it's Jinja template code, which we must NOT touch.
    # If the '...' is inside <script> blocks, we must NOT touch it.
    # Let's see: we can replace '...' with '…' in the text nodes of the HTML file.
    # But since there are no other '...' warnings in the audit, let's keep it simple.
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed accessibility issues in: {filepath}")
        return True
    return False

def main():
    templates_dir = 'templates'
    if not os.path.exists(templates_dir):
        print(f"Error: Directory '{templates_dir}' not found.")
        return

    fixed_count = 0
    for filename in os.listdir(templates_dir):
        if filename.endswith('.html'):
            filepath = os.path.join(templates_dir, filename)
            if fix_file(filepath):
                fixed_count += 1

    print(f"Completed! Fixed accessibility issues in {fixed_count} template files.")

if __name__ == '__main__':
    main()

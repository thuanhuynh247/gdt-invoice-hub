import os
import re
import sys
from bs4 import BeautifulSoup

def audit_file(filepath):
    errors = []
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Check for '...' vs '…'
    # Match three dots but not when part of a path or template code
    # Simple check for any literal '...' in text nodes
    soup = BeautifulSoup(content, 'html.parser')
    
    # 2. Check labels & inputs
    inputs = soup.find_all('input')
    for inp in inputs:
        inp_type = inp.get('type', 'text')
        inp_id = inp.get('id')
        
        # Skip buttons, radios, range, files, hidden, etc.
        if inp_type in ['button', 'submit', 'checkbox', 'radio', 'hidden', 'range', 'file']:
            continue
            
        # Check autocomplete
        if not inp.get('autocomplete'):
            # Print a warning/error
            line_no = find_line_number(content, str(inp)[:60])
            errors.append(f"Line {line_no}: Input (id='{inp_id}') lacks autocomplete attribute: {str(inp)[:80]}")
            
        # Check matching label or aria-label
        if not inp.get('aria-label') and not inp.get('aria-labelledby'):
            if inp_id:
                label = soup.find('label', attrs={'for': inp_id})
                if not label:
                    line_no = find_line_number(content, str(inp)[:60])
                    errors.append(f"Line {line_no}: Input (id='{inp_id}') lacks matching label or aria-label: {str(inp)[:80]}")
            else:
                line_no = find_line_number(content, str(inp)[:60])
                errors.append(f"Line {line_no}: Input lacks id and has no aria-label/aria-labelledby: {str(inp)[:80]}")

    # 3. Check decorative icons
    icons = soup.find_all('i', class_=lambda c: c and 'bi-' in c)
    for icon in icons:
        # Check if it has aria-hidden
        if not icon.get('aria-hidden'):
            line_no = find_line_number(content, str(icon)[:40])
            errors.append(f"Line {line_no}: Icon lacks aria-hidden='true': {str(icon)[:60]}")

    # 4. Check three dots in attributes (placeholder, etc.) or text
    # Search in raw file for three dots that are not template syntax
    # E.g. "... " or "..."
    # We find all matches and warn
    for match in re.finditer(r'\b\.\.\.\b|(?<=\w)\.\.\.(?=\s|$)|(?<=\s)\.\.\.(?=\w|$)', content):
        start = match.start()
        line_no = content[:start].count('\n') + 1
        errors.append(f"Line {line_no}: Literal '...' found. Use horizontal ellipsis '…' instead.")

    # Also search placeholders for literal "..."
    for elem in soup.find_all(placeholder=True):
        if '...' in elem['placeholder']:
            line_no = find_line_number(content, str(elem)[:50])
            errors.append(f"Line {line_no}: Element placeholder '{elem['placeholder']}' contains '...'. Use '…'.")

    return errors

def find_line_number(content, snippet):
    # Try to find the line number of a snippet in the raw content
    # Clean up snippet representation to match raw content
    snippet_clean = snippet.split('>')[0] # Get opening tag part
    idx = content.find(snippet_clean)
    if idx != -1:
        return content[:idx].count('\n') + 1
    return 'Unknown'

def main():
    templates_dir = 'templates'
    all_errors = {}
    
    if not os.path.exists(templates_dir):
        print(f"Error: Directory '{templates_dir}' not found.")
        sys.exit(1)
        
    for filename in os.listdir(templates_dir):
        if filename.endswith('.html'):
            filepath = os.path.join(templates_dir, filename)
            errors = audit_file(filepath)
            if errors:
                all_errors[filename] = errors
                
    if all_errors:
        print("\n=== UI/UX ACCESSIBILITY AUDIT REPORT ===")
        for filename, errors in all_errors.items():
            print(f"\n[{filename}]")
            for err in errors:
                print(f"  - {err}")
        print("\nAudit completed with issues found.")
        sys.exit(1)
    else:
        print("Audit completed. All templates follow UI/UX accessibility guidelines!")
        sys.exit(0)

if __name__ == '__main__':
    main()

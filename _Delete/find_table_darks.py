import glob
import re

print("Starting scan...")
for f in glob.glob('templates/**/*.html', recursive=True):
    try:
        with open(f, 'r', encoding='utf-8') as fh:
            content = fh.read()
    except Exception as e:
        continue
    matches = re.finditer(r'<thead[^>]*class="[^"]*table-dark[^"]*"[^>]*>', content)
    found = False
    for m in matches:
        if not found:
            print(f"\nFile: {f}")
            found = True
        line = content[:m.start()].count('\n') + 1
        print(f"  Line {line}: {m.group(0)}")
print("Scan completed.")

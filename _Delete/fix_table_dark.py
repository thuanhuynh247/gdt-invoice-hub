"""Batch remove 'table-dark' class from thead elements in compliance hub templates."""
import glob
import os

targets = sorted(glob.glob('templates/v*_compliance_hub.html'))
old_str = '<thead class="table-dark">'
new_str = '<thead>'

fixed = []
for f in targets:
    with open(f, 'r', encoding='utf-8') as fh:
        content = fh.read()
    if old_str in content:
        content = content.replace(old_str, new_str)
        with open(f, 'w', encoding='utf-8') as fh:
            fh.write(content)
        fixed.append(f)
        print(f'[FIXED] {f}')
    else:
        print(f'[CLEAN] {f}')

print(f'\nTotal fixed: {len(fixed)} files')

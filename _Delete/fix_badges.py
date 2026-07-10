"""Batch update baseline_card badge colors to subtle variants in compliance hub templates."""
import glob

# Define replacements
replacements = {
    "'bg-success text-white'": "'bg-success-subtle text-success border border-success-subtle'",
    "'bg-warning text-dark'": "'bg-warning-subtle text-warning border border-warning-subtle'",
    "'bg-danger text-white'": "'bg-danger-subtle text-danger border border-danger-subtle'",
    "'bg-info text-dark'": "'bg-info-subtle text-info border border-info-subtle'",
}

targets = sorted(glob.glob('templates/v5*_compliance_hub.html'))
fixed_count = 0

for f in targets:
    with open(f, 'r', encoding='utf-8') as fh:
        content = fh.read()
    original = content
    for old, new in replacements.items():
        content = content.replace(old, new)
    if content != original:
        with open(f, 'w', encoding='utf-8') as fh:
            fh.write(content)
        fixed_count += 1
        print(f'[FIXED] {f}')
    else:
        print(f'[CLEAN] {f}')

print(f'\nTotal fixed: {fixed_count} files')

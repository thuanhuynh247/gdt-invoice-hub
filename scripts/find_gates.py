with open('scripts/harness_win.py', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f):
        if 'completed' in line.lower():
            print(f"{idx+1}: {line.strip()}")

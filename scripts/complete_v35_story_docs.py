import os

def update_v35_docs():
    stories_dir = r"d:\LearnAnyThing\Webapp XML\docs\stories"
    v35_files = [
        "US-470-control-room-ui.md",
        "US-471-risk-stress-simulator.md",
        "US-472-defense-briefcase-builder.md",
        "US-473-tax-map-ui.md",
        "US-474-swarm-defense-chat.md",
        "US-475-e2e-test-suite.md"
    ]
    
    for filename in v35_files:
        filepath = os.path.join(stories_dir, filename)
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            continue
            
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Update status
        content = content.replace("Status\nplanned", "Status\ncompleted")
        content = content.replace("status\nplanned", "status\ncompleted")
        content = content.replace("Status\nin_progress", "Status\ncompleted")
        content = content.replace("status\nin_progress", "status\ncompleted")
        
        # Check acceptance criteria boxes
        content = content.replace("- [ ]", "- [x]")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"Updated docs for: {filename}")

if __name__ == "__main__":
    update_v35_docs()

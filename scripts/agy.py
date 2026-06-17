import sys
import os
import urllib.request
import zipfile
import shutil
import tempfile
import re
from pathlib import Path

def print_help():
    print("Antigravity CLI (agy)")
    print("Usage:")
    print("  agy plugin install <github_url>")
    print("  agy plugin list")
    sys.exit(1)

def list_plugins(skills_dir):
    print("Installed skills/plugins:")
    for path in skills_dir.iterdir():
        if path.is_dir() and (path / "SKILL.md").exists():
            print(f"  - {path.name}")

def install_plugin(repo_url, skills_dir, workspace_dir):
    # Normalize github url
    match = re.match(r'https?://github\.com/([^/]+)/([^/.]+)(?:\.git)?', repo_url)
    if not match:
        print(f"Error: Invalid GitHub URL: {repo_url}")
        print("Must be in format: https://github.com/owner/repo")
        sys.exit(1)
        
    owner, repo = match.groups()
    repo_name = repo.lower()
    
    print(f"Installing plugin/skill '{repo_name}' from {repo_url}...")
    
    # Create temp download path
    scratch_dir = workspace_dir / "scratch"
    scratch_dir.mkdir(exist_ok=True)
    temp_zip = scratch_dir / f"{repo_name}_temp.zip"
    extract_dir = scratch_dir / f"{repo_name}_temp_extract"
    
    # Clean up old extraction
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
        
    # Attempt download main.zip, fallback to master.zip
    urls_to_try = [
        f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip",
        f"https://github.com/{owner}/{repo}/archive/refs/heads/master.zip"
    ]
    
    downloaded = False
    for url in urls_to_try:
        try:
            print(f"Trying download from {url}...")
            # Set a user-agent to avoid Github blocking
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req) as response:
                with open(temp_zip, 'wb') as out_file:
                    shutil.copyfileobj(response, out_file)
            downloaded = True
            break
        except Exception as e:
            print(f"Download from {url} failed: {e}")
            
    if not downloaded:
        print("Error: Failed to download repository archive.")
        sys.exit(1)
        
    # Unzip
    print("Extracting repository content...")
    try:
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
    except Exception as e:
        print(f"Error extracting zip: {e}")
        # cleanup
        if temp_zip.exists():
            temp_zip.unlink()
        sys.exit(1)
        
    # Find the root extracted folder
    extracted_root = None
    for child in extract_dir.iterdir():
        if child.is_dir():
            extracted_root = child
            break
            
    if not extracted_root:
        print("Error: Could not find extracted root folder.")
        sys.exit(1)
        
    # Find rules / instructions files
    rule_files = []
    
    # Traverse directory and find potential instruction/rule files
    for root, dirs, files in os.walk(extracted_root):
        for file in files:
            file_path = Path(root) / file
            rel_path = file_path.relative_to(extracted_root)
            # Look for copilot-instructions, cursor rules, or generic instructions
            if (
                file.endswith('.mdc') or
                'instruction' in file.lower() or
                'rule' in file.lower() or
                file == 'README.md'
            ):
                rule_files.append((file_path, rel_path))
                
    if not rule_files:
        # If no specific rule files, search for any md file
        for root, dirs, files in os.walk(extracted_root):
            for file in files:
                if file.endswith('.md'):
                    file_path = Path(root) / file
                    rel_path = file_path.relative_to(extracted_root)
                    rule_files.append((file_path, rel_path))
                    
    print(f"Found {len(rule_files)} rule/documentation files.")
    
    # Create the target skill directory
    target_skill_dir = skills_dir / repo_name
    target_skill_dir.mkdir(exist_ok=True)
    
    target_ref_dir = target_skill_dir / "references"
    target_ref_dir.mkdir(exist_ok=True)
    
    # Copy rule files to references
    copied_files = []
    for src_path, rel_path in rule_files:
        # Flatten name slightly to avoid nested reference dirs in skill if simple,
        # or recreate structure. Let's make a flat filename.
        flat_name = rel_path.as_posix().replace('/', '_')
        dest_path = target_ref_dir / flat_name
        shutil.copy2(src_path, dest_path)
        copied_files.append(flat_name)
        print(f"  Copied {rel_path} -> references/{flat_name}")
        
    # Determine description and details
    description = f"Rules and workflows derived from {repo_name}."
    
    # Try to extract a brief description from one of the files
    for src_path, _ in rule_files:
        content = src_path.read_text(encoding='utf-8', errors='ignore')
        desc_match = re.search(r'description:\s*(.+)', content)
        if desc_match:
            desc_val = desc_match.group(1).strip()
            # Under 200 chars check
            if len(desc_val) < 200:
                description = desc_val
                break
                
    # Create SKILL.md
    skill_md_content = f"""---
name: {repo_name}
description: {description}
license: MIT
version: 1.0.0
---

# {repo_name.capitalize()}

## Overview
This skill implements the instructions and rules defined in the {repo_name} repository.

## Reference Rules
Refer to the following reference files for detailed instructions:
"""
    for copied_file in copied_files:
        skill_md_content += f"- [{copied_file}](file:///C:/Users/THUAN/.gemini/antigravity/skills/{repo_name}/references/{copied_file})\n"
        
    skill_md_content += """
## Instructions
- Ensure these rules are followed whenever editing files or implementing features related to this topic.
- Use progressive disclosure: read the reference documents in the references folder for specific guidance when needed.
"""
    
    skill_md_path = target_skill_dir / "SKILL.md"
    skill_md_path.write_text(skill_md_content, encoding='utf-8')
    print("Created SKILL.md")
    
    # Clean up temp files
    temp_zip.unlink()
    shutil.rmtree(extract_dir)
    print("Cleaned up temporary download files.")
    
    # Run validator
    validator_path = Path("C:/Users/THUAN/.gemini/antigravity/skills/skill-creator/scripts/quick_validate.py")
    if validator_path.exists():
        import subprocess
        print("Validating skill structure...")
        res = subprocess.run([sys.executable, str(validator_path), str(target_skill_dir)], capture_output=True, text=True)
        print(res.stdout.strip())
        
    print(f"Skill '{repo_name}' installed successfully!")

def main():
    if len(sys.argv) < 2:
        print_help()
        
    cmd = sys.argv[1]
    skills_dir = Path("C:/Users/THUAN/.gemini/antigravity/skills")
    workspace_dir = Path("d:/LearnAnyThing/Webapp XML")
    
    if cmd == "plugin":
        if len(sys.argv) < 3:
            print_help()
        subcmd = sys.argv[2]
        if subcmd == "install":
            if len(sys.argv) < 4:
                print_help()
            repo_url = sys.argv[3]
            install_plugin(repo_url, skills_dir, workspace_dir)
        elif subcmd == "list":
            list_plugins(skills_dir)
        else:
            print_help()
    else:
        print_help()

if __name__ == "__main__":
    main()

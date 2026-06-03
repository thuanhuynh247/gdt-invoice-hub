#!/usr/bin/env python
"""
Release Packaging Script
Compresses the application codebase into a clean ZIP file for local distribution,
excluding virtual environments, caches, temporary files, and local databases.
"""

import os
import zipfile
import sys

def package_project():
    # Target archive name
    archive_name = "invoice_webapp_release.zip"
    
    # Excluded directories (exact match or prefix match)
    exclude_dirs = {
        '.git',
        '.github',
        'venv',
        '__pycache__',
        '.pytest_cache',
        'data',
        'scratch',
        'tmp_pip_build',
        '.better-agents-clone',
        '.cache',
        '.harness-backup',
        '.harness-clone',
        '.skills-clone',
        'chromedriver',
        'open-design',
        '.understand-anything',
        '.codex',
        '.khuym',
        '.code-review-graph',
        '.codegraph',
        'temp_understand',
        'temp_ag_kit',
        'gdt-invoice-hub'
    }
    
    # Excluded files
    exclude_files = {
        '.coverage',
        '.env',
        archive_name
    }
    
    # File extensions to ignore
    exclude_extensions = {'.pyc', '.pyo', '.pyd', '.db'}
    
    print(f"📦 Compiling files for {archive_name}...")
    
    count = 0
    with zipfile.ZipFile(archive_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk('.'):
            # Modify dirs in-place to avoid walking down excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.chrome_user_data_')]
            
            for file in files:
                if file in exclude_files:
                    continue
                
                _, ext = os.path.splitext(file)
                if ext.lower() in exclude_extensions:
                    continue
                
                file_path = os.path.join(root, file)
                # Strip leading './' if present
                archive_path = os.path.relpath(file_path, '.')
                
                # Double check that we are not adding any files inside excluded folders
                path_parts = archive_path.split(os.sep)
                if any(part in exclude_dirs for part in path_parts) or any(part.startswith('.chrome_user_data_') for part in path_parts):
                    continue
                
                zipf.write(file_path, archive_path)
                count += 1
                
    print(f"✅ Success! Packed {count} files into {archive_name}")
    return archive_name

if __name__ == "__main__":
    package_project()

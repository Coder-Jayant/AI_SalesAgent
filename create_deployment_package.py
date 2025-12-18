#!/usr/bin/env python3
"""
Create Production Deployment Package

Creates a zip archive of the project with all necessary files,
excluding development artifacts and sensitive data.

Usage:
    python create_deployment_package.py
"""

import os
import zipfile
import shutil
from pathlib import Path
from datetime import datetime

# Files and directories to exclude from the package
EXCLUDE_PATTERNS = [
    '__pycache__',
    '*.pyc',
    '*.pyo',
    '*.pyd',
    '.git',
    '.gitignore',
    '.vscode',
    '.idea',
    '*.log',
    '*.log.*',
    'test_report.json',
    'autopilot.lock',
    'action_plans_execution.lock',
    'autopilot_stop.flag',
    # Don't include state files with potentially sensitive data
    'autopilot_state.json',
    'action_plans_state.json',
    'processed_mails.json',
    'rag_state.json',
    'ews_accounts.json',
    # Don't include .env (user must configure their own)
    '.env',
    # Don't include large binary files
    '*.exe',
    # Don't include backup directories
    'action_plans_backups',
    # Don't include this script itself in the archive
    'create_deployment_package.py'
]

# Files to definitely include
REQUIRED_FILES = [
    'main_react.py',
    'autopilot.py',
    'autopilot_service.py',
    'action_plan_service.py',
    'autopilot_control.py',
    'react_agent.py',
    'agent_tools.py',
    'ews_tools2.py',
    'action_handlers.py',
    'scheduled_tasks.py',
    'rag_backend.py',
    'rag_manager.py',
    'ews_config.py',
    'frequency_formatter.py',
    'requirements.txt',
    'README.md',
    # Service files
    '*.service',
    '*.bat',
    '*.sh',
    # Documentation
    '*.md',
    # Template files
    '.env.template'
]

def should_exclude(path, exclude_patterns):
    """Check if a path should be excluded"""
    path_str = str(path)
    name = path.name
    
    for pattern in exclude_patterns:
        if pattern.startswith('*.'):
            # File extension pattern
            if name.endswith(pattern[1:]):
                return True
        elif pattern.endswith('*'):
            # Prefix pattern
            if name.startswith(pattern[:-1]):
                return True
        else:
            # Exact match
            if name == pattern or path_str.endswith(pattern):
                return True
    
    return False

def create_env_template():
    """Create .env.template from .env if it doesn't exist"""
    env_path = Path('.env')
    template_path = Path('.env.template')
    
    if env_path.exists() and not template_path.exists():
        print("Creating .env.template from .env...")
        
        with open(env_path, 'r') as f_in, open(template_path, 'w') as f_out:
            for line in f_in:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Replace values with placeholders
                    if '=' in line:
                        key = line.split('=')[0]
                        f_out.write(f"{key}=YOUR_VALUE_HERE\n")
                    else:
                        f_out.write(line + '\n')
                else:
                    f_out.write(line + '\n')
        
        print("✓ .env.template created")
        return True
    elif template_path.exists():
        print("✓ .env.template already exists")
        return True
    else:
        print("⚠ No .env file found to create template from")
        return False

def create_deployment_package():
    """Create the deployment package"""
    print("=" * 60)
    print("Creating Production Deployment Package")
    print("=" * 60)
    print()
    
    # Get project directory
    project_dir = Path.cwd()
    project_name = project_dir.name
    
    # Create timestamp for archive name
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    archive_name = f"{project_name}_deployment_{timestamp}.zip"
    archive_path = project_dir.parent / archive_name
    
    print(f"Project: {project_name}")
    print(f"Archive: {archive_name}")
    print(f"Location: {archive_path.parent}")
    print()
    
    # Create .env.template if needed
    create_env_template()
    print()
    
    # Count files
    total_files = 0
    included_files = 0
    excluded_files = 0
    
    print("Scanning project files...")
    
    # Create the zip file
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(project_dir):
            # Remove excluded directories from dirs list
            dirs[:] = [d for d in dirs if not should_exclude(Path(root) / d, EXCLUDE_PATTERNS)]
            
            for file in files:
                total_files += 1
                file_path = Path(root) / file
                relative_path = file_path.relative_to(project_dir)
                
                # Check if should exclude
                if should_exclude(file_path, EXCLUDE_PATTERNS):
                    excluded_files += 1
                    print(f"  Excluding: {relative_path}")
                    continue
                
                # Add to archive
                arcname = str(relative_path).replace('\\', '/')
                zipf.write(file_path, arcname)
                included_files += 1
                print(f"  ✓ Added: {relative_path}")
    
    print()
    print("=" * 60)
    print("Package Creation Complete!")
    print("=" * 60)
    print()
    print(f"Total files scanned: {total_files}")
    print(f"Files included: {included_files}")
    print(f"Files excluded: {excluded_files}")
    print()
    print(f"Package created: {archive_path}")
    print(f"Package size: {archive_path.stat().st_size / (1024*1024):.2f} MB")
    print()
    print("IMPORTANT REMINDERS:")
    print("1. Configure .env file on target server")
    print("2. Install Python dependencies: pip install -r requirements.txt")
    print("3. Set up virtual environment if needed")
    print("4. Run test_services_comprehensive.py before production")
    print("5. Install services using install_*_service scripts")
    print()
    
    return archive_path

if __name__ == "__main__":
    try:
        package_path = create_deployment_package()
        print(f"✓ Deployment package ready: {package_path.name}")
    except Exception as e:
        print(f"✗ Error creating package: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

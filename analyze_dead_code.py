import os
import re
from pathlib import Path
from collections import defaultdict

alas_wrapped_path = Path('alas_wrapped')
upstream_path = Path('upstream_alas')

# Get all Python files in alas_wrapped/module
print("Scanning module files...")
module_files = {}
for f in (alas_wrapped_path / 'module').rglob('*.py'):
    if '__pycache__' not in str(f) and 'venv' not in str(f):
        rel_path = f.relative_to(alas_wrapped_path / 'module')
        module_path = str(rel_path).replace('\\', '/').replace('.py', '')
        file_name = f.stem
        module_files[module_path] = {
            'file_name': file_name,
            'full_path': str(f).replace('\\', '/'),
            'rel_path': str(rel_path).replace('\\', '/')
        }

print(f"Found {len(module_files)} module files to check")

# Read all Python files in alas_wrapped to find imports
print("Scanning for imports...")
all_imports = defaultdict(list)

# Only scan Python files, not all files
py_files = list(alas_wrapped_path.rglob('*.py'))
print(f"Scanning {len(py_files)} Python files...")

count = 0
for py_file in py_files:
    if '__pycache__' in str(py_file) or 'venv' in str(py_file):
        continue
    
    count += 1
    if count % 100 == 0:
        print(f"  Processed {count}/{len(py_files)} files...")
    
    try:
        with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as exc:
        print(f'[WARN] Failed to read {py_file}: {exc}')
        continue
    
    rel_file = str(py_file.relative_to(alas_wrapped_path)).replace('\\', '/')
    
    # Find various import patterns
    for module_path, info in module_files.items():
        module_dot = module_path.replace('/', '.')
        # Pattern: from module.X import ...
        pattern1 = rf'from\s+module\.{module_dot}\b'
        # Pattern: import module.X
        pattern2 = rf'import\s+module\.{module_dot}\b'
        
        if re.search(pattern1, content) or re.search(pattern2, content):
            all_imports[module_path].append(rel_file)

print("\n" + '=' * 80)
print('POTENTIALLY DEAD/ORPHANED FILES IN alas_wrapped/module')
print('=' * 80)

dead_files = []
for module_path, info in sorted(module_files.items()):
    importers = all_imports.get(module_path, [])
    if not importers:
        dead_files.append((module_path, info))

print(f'\nFound {len(dead_files)} files with no detected imports:\n')

for module_path, info in sorted(dead_files):
    print(f'  {info["rel_path"]}')
    print(f'    - File name: {info["file_name"]}')
    
    # Check if this file exists in upstream
    upstream_file = upstream_path / 'module' / info['rel_path']
    if upstream_file.exists():
        print(f'    - Status: EXISTS in upstream_alas')
    else:
        print(f'    - Status: CUSTOM (not in upstream)')
    print()

# Summary by category
print('=' * 80)
print('SUMMARY BY CATEGORY')
print('=' * 80)

custom_dead = []
upstream_dead = []

for module_path, info in dead_files:
    upstream_file = upstream_path / 'module' / info['rel_path']
    if upstream_file.exists():
        upstream_dead.append(info['rel_path'])
    else:
        custom_dead.append(info['rel_path'])

print(f"\n1. CUSTOM files (not in upstream) with no imports: {len(custom_dead)}")
for f in sorted(custom_dead):
    print(f"   - {f}")

print(f"\n2. UPSTREAM files with no imports: {len(upstream_dead)}")
for f in sorted(upstream_dead):
    print(f"   - {f}")

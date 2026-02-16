import re
from pathlib import Path

dead_files = [
    'config/redirect_utils/os_handler.py',
    'device/method/scrcpy/__init__.py',
    'device/method/scrcpy/scrcpy.py',
    'device/pkg_resources/__init__.py',
    'device/platform/__init__.py',
    'game_setting/setting_generated.py',
    'map_detection/detector_example.py',
    'notify/__init__.py',
    'research/preset_generator.py',
    'statistics/drop_statistics.py',
    'webui/__init__.py',
    'webui/translate.py',
]

alas_wrapped_path = Path('alas_wrapped')
upstream_path = Path('upstream_alas')

print('=' * 80)
print('DETAILED ANALYSIS OF POTENTIALLY DEAD FILES')
print('=' * 80)

for df in dead_files:
    file_path = alas_wrapped_path / 'module' / df
    print(f'\n## {df}')
    print('-' * 60)
    
    # Check file size and content
    if file_path.exists():
        size = file_path.stat().st_size
        print(f'Size: {size} bytes')
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        lines = content.split('\n')
        non_empty = [l for l in lines if l.strip()]
        print(f'Lines: {len(lines)}, Non-empty: {len(non_empty)}')
        
        # Check for class definitions
        classes = re.findall(r'^class\s+(\w+)', content, re.MULTILINE)
        if classes:
            class_str = ', '.join(classes)
            print(f'Classes: {class_str}')
        
        # Check for function definitions
        functions = re.findall(r'^def\s+(\w+)', content, re.MULTILINE)
        if functions:
            func_str = ', '.join(functions[:5])
            if len(functions) > 5:
                func_str += '...'
            print(f'Functions: {func_str}')
        
        # Check for any string references in all files
        file_name = Path(df).stem
        if file_name not in ['__init__']:
            # Search for any reference to this module name
            pattern = rf'\b{file_name}\b'
            refs = []
            for py_file in alas_wrapped_path.rglob('*.py'):
                if '__pycache__' in str(py_file):
                    continue
                try:
                    with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                        fc = f.read()
                    if re.search(pattern, fc):
                        refs.append(str(py_file.relative_to(alas_wrapped_path)).replace('\\', '/'))
                except:
                    continue
            if refs:
                print(f'Possible references (by name): {len(refs)} files')
                for r in refs[:3]:
                    print(f'    - {r}')
    else:
        print('File not found!')

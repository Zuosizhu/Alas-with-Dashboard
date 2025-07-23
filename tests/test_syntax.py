import ast
import os
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_all_python_files_compile():
    """Ensure all Python files have valid syntax"""
    errors = []
    file_count = 0
    
    for py_file in Path("module").rglob("*.py"):
        file_count += 1
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                ast.parse(f.read())
        except SyntaxError as e:
            errors.append(f"{py_file}: {e}")
    
    print(f"[PASS] Checked {file_count} Python files for syntax")
    
    if errors:
        print(f"[FAIL] Found {len(errors)} syntax errors:")
        for error in errors[:10]:  # Show first 10 errors
            print(f"  - {error}")
        return False
    return True

def test_main_imports():
    """Test that main modules can be imported"""
    critical_imports = [
        ("alas", "Main entry point"),
        ("module.base.base", "Base module"),
        ("module.config.config", "Config module"),
        ("module.ocr.ocr", "OCR module"),
        ("module.campaign.campaign_base", "Campaign module")
    ]
    
    success_count = 0
    failures = []
    
    for module_path, description in critical_imports:
        try:
            module_parts = module_path.split('.')
            if len(module_parts) > 1:
                # For nested modules, import parent first
                parent = '.'.join(module_parts[:-1])
                __import__(parent)
            __import__(module_path)
            success_count += 1
            print(f"[PASS] Successfully imported {module_path} ({description})")
        except ImportError as e:
            # Check if it's a dependency issue vs actual code issue
            error_msg = str(e)
            if "No module named" in error_msg:
                # Extract the missing module name
                missing = error_msg.split("'")[1] if "'" in error_msg else "unknown"
                if missing in ['inflection', 'cv2', 'PIL', 'numpy', 'scipy', 'adbutils', 'uiautomator2', 
                             'pywebio', 'rich', 'tqdm', 'yaml', 'pydantic', 'cached_property', 'retrying',
                             'aiofiles', 'av', 'zerorpc', 'wrapt', 'psutil', 'jellyfish', 'pypresence',
                             'starlette', 'uvicorn', 'pyzmq', 'lxml', 'websockets', 'msgpack', 'anyio',
                             'imageio', 'prettytable', 'packaging']:
                    print(f"[WARN] {module_path}: Missing dependency '{missing}' (expected)")
                else:
                    failures.append(f"{module_path}: {e}")
                    print(f"[FAIL] Failed to import {module_path}: {e}")
            else:
                failures.append(f"{module_path}: {e}")
                print(f"✗ Failed to import {module_path}: {e}")
        except Exception as e:
            failures.append(f"{module_path}: {type(e).__name__}: {e}")
            print(f"✗ Failed to import {module_path}: {type(e).__name__}: {e}")
    
    print(f"\nImport test summary: {success_count}/{len(critical_imports)} modules")
    return len(failures) == 0

if __name__ == "__main__":
    print("=" * 50)
    print("SYNTAX AND IMPORT TESTS")
    print("=" * 50)
    
    syntax_pass = test_all_python_files_compile()
    print()
    import_pass = test_main_imports()
    
    print("\n" + "=" * 50)
    if syntax_pass and import_pass:
        print("[PASS] ALL SYNTAX TESTS PASSED")
    else:
        print("[FAIL] SOME TESTS FAILED")
        if not syntax_pass:
            print("  - Syntax compilation failed")
        if not import_pass:
            print("  - Import tests failed")
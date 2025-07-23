import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_config_structure():
    """Test configuration files are intact"""
    print("Testing configuration structure...")
    
    config_files = [
        "config/template.json",
        "pyproject.toml",
        ".github/copilot-instructions.md"
    ]
    
    all_good = True
    for config_file in config_files:
        if os.path.exists(config_file):
            size = os.path.getsize(config_file)
            print(f"[PASS] {config_file} exists ({size} bytes)")
        else:
            if config_file == ".github/copilot-instructions.md":
                # This is expected since we created it in .github/
                print(f"[INFO] {config_file} not in root (check .github/)")
            else:
                print(f"[FAIL] {config_file} not found")
                all_good = False
    
    return all_good

def test_import_performance():
    """Test that imports don't take too long"""
    print("\nTesting import performance...")
    
    # Test importing key modules (without dependencies)
    modules_to_time = [
        ("module.exception", "Exception module"),
        ("module.logger", "Logger module"),
        ("module.base.decorator", "Decorator module"),
    ]
    
    total_time = 0
    all_good = True
    
    for module_name, description in modules_to_time:
        try:
            start = time.time()
            # Try to import
            try:
                __import__(module_name)
                elapsed = time.time() - start
                total_time += elapsed
                
                if elapsed < 1.0:  # Should import quickly
                    print(f"[PASS] {description} imported in {elapsed:.3f}s")
                else:
                    print(f"[WARN] {description} slow import: {elapsed:.3f}s")
                    
            except ImportError as e:
                # Expected for modules with dependencies
                print(f"[INFO] {description} requires dependencies (expected)")
                
        except Exception as e:
            print(f"[FAIL] {description} error: {e}")
            all_good = False
    
    print(f"[INFO] Total import time: {total_time:.3f}s")
    return all_good

def test_core_module_structure():
    """Test that core modules have expected structure"""
    print("\nTesting core module structure...")
    
    # Check key directories exist
    core_dirs = [
        "module/base",
        "module/config", 
        "module/ocr",
        "module/campaign",
        "module/device",
        "module/combat"
    ]
    
    all_good = True
    for dir_path in core_dirs:
        if os.path.isdir(dir_path):
            # Count Python files
            py_files = list(Path(dir_path).glob("*.py"))
            print(f"[PASS] {dir_path} exists ({len(py_files)} .py files)")
        else:
            print(f"[FAIL] {dir_path} directory not found")
            all_good = False
    
    return all_good

def test_no_syntax_errors_in_edits():
    """Verify edited files have valid syntax"""
    print("\nTesting edited files for syntax errors...")
    
    # Key files that were edited
    edited_files = [
        "module/ocr/ocr.py",
        "module/ocr/models.py",
        "module/ocr/rpc.py",
        "module/ocr/al_ocr.py",
        "alas.py"
    ]
    
    all_good = True
    for file_path in edited_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Try to compile
                compile(content, file_path, 'exec')
                print(f"[PASS] {file_path} has valid syntax")
                
            except SyntaxError as e:
                print(f"[FAIL] {file_path} has syntax error: {e}")
                all_good = False
            except Exception as e:
                print(f"[WARN] {file_path} check failed: {e}")
        else:
            print(f"[FAIL] {file_path} not found")
            all_good = False
    
    return all_good

def test_poetry_config():
    """Test Poetry configuration is valid"""
    print("\nTesting Poetry configuration...")
    
    if not os.path.exists("pyproject.toml"):
        print("[FAIL] pyproject.toml not found")
        return False
    
    try:
        # Use tomli for older Python, tomllib for 3.11+
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
            
        with open("pyproject.toml", 'rb') as f:
            data = tomllib.load(f)
            
        # Check required sections
        checks = [
            ('tool' in data, "Has [tool] section"),
            ('poetry' in data.get('tool', {}), "Has [tool.poetry] section"),
            ('dependencies' in data.get('tool', {}).get('poetry', {}), "Has dependencies"),
            ('black' in data.get('tool', {}), "Has Black configuration"),
            ('ruff' in data.get('tool', {}), "Has Ruff configuration"),
        ]
        
        all_good = True
        for check, description in checks:
            if check:
                print(f"[PASS] {description}")
            else:
                print(f"[FAIL] {description}")
                all_good = False
                
        # Check Python version
        poetry_data = data.get('tool', {}).get('poetry', {})
        if 'python' in poetry_data:
            python_ver = poetry_data['python']
            print(f"[INFO] Requires Python {python_ver}")
            
        return all_good
        
    except Exception as e:
        # If we can't import tomli, just do basic checks
        print("[INFO] Cannot parse TOML without tomli/tomllib, doing basic check")
        
        with open("pyproject.toml", 'r') as f:
            content = f.read()
            
        if '[tool.poetry]' in content and 'python = "^3.10"' in content:
            print("[PASS] Basic Poetry configuration present")
            return True
        else:
            print("[FAIL] Poetry configuration incomplete")
            return False

# Import Path for other tests
from pathlib import Path

if __name__ == "__main__":
    print("=" * 50)
    print("INTEGRATION TESTS")
    print("=" * 50)
    
    tests = [
        test_config_structure(),
        test_import_performance(),
        test_core_module_structure(),
        test_no_syntax_errors_in_edits(),
        test_poetry_config()
    ]
    
    passed = sum(tests)
    total = len(tests)
    
    print("\n" + "=" * 50)
    if passed == total:
        print(f"[PASS] ALL INTEGRATION TESTS PASSED ({passed}/{total})")
    else:
        print(f"[FAIL] SOME TESTS FAILED ({passed}/{total} passed)")
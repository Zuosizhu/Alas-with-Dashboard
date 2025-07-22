#!/usr/bin/env python3
"""
Tesseract OCR Installation Helper for ALAS
"""
import os
import sys
import subprocess
import platform

def check_tesseract():
    """Check if Tesseract is installed and accessible"""
    try:
        result = subprocess.run(['tesseract', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("[OK] Tesseract is already installed:")
            print(result.stdout.split('\n')[0])
            return True
    except FileNotFoundError:
        pass
    return False

def check_pytesseract():
    """Check if pytesseract Python package is installed"""
    try:
        import pytesseract
        print("[OK] pytesseract Python package is installed")
        return True
    except ImportError:
        print("[MISSING] pytesseract Python package is not installed")
        return False

def install_instructions():
    """Provide platform-specific installation instructions"""
    system = platform.system()
    
    print("\n" + "="*60)
    print("Tesseract OCR Installation Instructions")
    print("="*60)
    
    if system == "Windows":
        print("\nFor Windows:")
        print("1. Download Tesseract installer from:")
        print("   https://github.com/UB-Mannheim/tesseract/wiki")
        print("   (Get the latest 64-bit installer)")
        print("\n2. Run the installer and:")
        print("   - Install to: C:\\Program Files\\Tesseract-OCR")
        print("   - During installation, expand 'Additional language data'")
        print("   - Select these languages:")
        print("     [*] English (eng) - Default")
        print("     [*] Japanese (jpn)")
        print("     [*] Chinese - Simplified (chi_sim)")
        print("     [*] Chinese - Traditional (chi_tra)")
        print("\n3. Add Tesseract to PATH:")
        print("   - Add 'C:\\Program Files\\Tesseract-OCR' to system PATH")
        print("   - Restart your command prompt/terminal")
        
    elif system == "Linux":
        print("\nFor Linux (Ubuntu/Debian):")
        print("sudo apt update")
        print("sudo apt install tesseract-ocr")
        print("sudo apt install tesseract-ocr-eng")
        print("sudo apt install tesseract-ocr-jpn")
        print("sudo apt install tesseract-ocr-chi-sim")
        print("sudo apt install tesseract-ocr-chi-tra")
        
    elif system == "Darwin":  # macOS
        print("\nFor macOS:")
        print("brew install tesseract")
        print("brew install tesseract-lang")
    
    print("\n4. Install Python package:")
    print("   pip install pytesseract")
    print("\n5. Test installation by running this script again")

def test_ocr():
    """Test basic OCR functionality"""
    try:
        import pytesseract
        from PIL import Image, ImageDraw, ImageFont
        import numpy as np
        
        # Create a simple test image
        img = Image.new('RGB', (200, 50), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "TEST 123", fill='black')
        
        # Convert to numpy array
        img_array = np.array(img)
        
        # Try OCR
        result = pytesseract.image_to_string(img_array)
        if "TEST" in result or "123" in result:
            print("\n[OK] OCR test successful!")
            print(f"  Recognized: {result.strip()}")
            return True
        else:
            print("\n[FAIL] OCR test failed")
            return False
    except Exception as e:
        print(f"\n[FAIL] OCR test failed: {e}")
        return False

def main():
    print("ALAS Tesseract OCR Setup")
    print("="*60)
    
    # Check Tesseract executable
    tesseract_installed = check_tesseract()
    
    # Check pytesseract package
    pytesseract_installed = check_pytesseract()
    
    if not tesseract_installed:
        install_instructions()
        return
    
    if not pytesseract_installed:
        print("\nInstalling pytesseract...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pytesseract'])
        pytesseract_installed = check_pytesseract()
    
    if tesseract_installed and pytesseract_installed:
        print("\n[OK] All dependencies installed!")
        
        # Test OCR
        print("\nTesting OCR functionality...")
        if test_ocr():
            print("\n[OK] Tesseract is ready for ALAS!")
            
            # Check for language packs
            print("\nChecking language support...")
            try:
                import pytesseract
                langs = pytesseract.get_languages()
                required_langs = ['eng', 'jpn', 'chi_sim', 'chi_tra']
                
                for lang in required_langs:
                    if lang in langs:
                        print(f"  [OK] {lang} installed")
                    else:
                        print(f"  [MISSING] {lang} NOT installed - OCR may not work for this language")
                        
            except Exception as e:
                print(f"Could not check languages: {e}")

if __name__ == "__main__":
    main()
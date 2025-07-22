# Immediate Action Plan: ALAS Modernization

## Current Situation
- Previous agent removed OCR but left broken stubs
- Original uses `cnocr` with MXNet (heavy dependencies)
- Models are missing from `./bin/cnocr_models/`
- Python code uses outdated syntax

## Immediate Steps (What We Can Do Now)

### Step 1: Create Tesseract-based OCR Replacement
Since the models are missing anyway, we'll implement a Tesseract-based solution:

```python
# module/ocr/tesseract_backend.py
import pytesseract
import cv2
import numpy as np
from typing import List, Optional

class TesseractBackend:
    """Drop-in replacement for AlOcr using Tesseract"""
    
    def __init__(self, lang='eng', whitelist=None):
        self.lang = self._map_language(lang)
        self.whitelist = whitelist
        self.config = self._build_config()
    
    def _map_language(self, alas_lang: str) -> str:
        """Map ALAS language codes to Tesseract"""
        mapping = {
            'azur_lane': 'eng',
            'azur_lane_jp': 'jpn+eng', 
            'cnocr': 'chi_sim+eng',
            'jp': 'jpn',
            'tw': 'chi_tra'
        }
        return mapping.get(alas_lang, 'eng')
    
    def _build_config(self) -> str:
        """Build Tesseract config string"""
        config = '--psm 7'  # Single text line
        if self.whitelist:
            config += f' -c tessedit_char_whitelist={self.whitelist}'
        return config
    
    def ocr(self, image: np.ndarray) -> str:
        """Main OCR method"""
        try:
            # Ensure image is in the right format
            if len(image.shape) == 3:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply preprocessing
            image = self._preprocess(image)
            
            # Run OCR
            text = pytesseract.image_to_string(
                image, 
                lang=self.lang,
                config=self.config
            ).strip()
            
            return text
        except Exception as e:
            logger.warning(f"Tesseract OCR failed: {e}")
            return ""
    
    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for better OCR"""
        # Scale up small images
        height, width = image.shape[:2]
        if height < 32:
            scale = 32 / height
            new_width = int(width * scale)
            image = cv2.resize(image, (new_width, 32), interpolation=cv2.INTER_CUBIC)
        
        # Apply threshold
        _, image = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Add border
        image = cv2.copyMakeBorder(image, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=255)
        
        return image
    
    def ocr_for_single_line(self, image: np.ndarray) -> str:
        """Optimized for single line"""
        return self.ocr(image)
    
    def ocr_for_single_lines(self, images: List[np.ndarray]) -> List[str]:
        """OCR multiple images"""
        return [self.ocr(img) for img in images]
    
    def atomic_ocr_for_single_lines(self, images: List[np.ndarray], alphabet=None) -> List[List[str]]:
        """Match AlOcr interface"""
        old_whitelist = self.whitelist
        if alphabet:
            self.whitelist = alphabet
            self.config = self._build_config()
        
        results = []
        for img in images:
            text = self.ocr(img)
            # Return as list of characters to match original
            results.append(list(text))
        
        self.whitelist = old_whitelist
        self.config = self._build_config()
        
        return results
```

### Step 2: Update OCR Module Files

1. **Fix `module/ocr/al_ocr.py`**:
```python
# Replace the entire file with:
from module.ocr.tesseract_backend import TesseractBackend

class AlOcr(TesseractBackend):
    """Compatibility wrapper for existing code"""
    
    def __init__(self, model_name='densenet-lite-gru', model_epoch=None,
                 cand_alphabet=None, root=None, context='cpu', name=None):
        # Map name to language
        lang_map = {
            'azur_lane': 'azur_lane',
            'azur_lane_jp': 'azur_lane_jp',
            'cnocr': 'cnocr',
            'jp': 'jp',
            'tw': 'tw'
        }
        lang = lang_map.get(name, 'azur_lane')
        super().__init__(lang=lang, whitelist=cand_alphabet)
        self.name = name
    
    def set_cand_alphabet(self, alphabet):
        """Set character whitelist"""
        self.whitelist = alphabet
        self.config = self._build_config()
    
    def atomic_ocr(self, image, alphabet=None):
        """Atomic OCR with alphabet"""
        if alphabet:
            self.set_cand_alphabet(alphabet)
        return self.ocr(image)
```

2. **Fix `module/ocr/models.py`**:
```python
from module.base.decorator import cached_property
from module.ocr.al_ocr import AlOcr

class OcrModel:
    @cached_property
    def azur_lane(self):
        return AlOcr(name='azur_lane')
    
    @cached_property
    def azur_lane_jp(self):
        return AlOcr(name='azur_lane_jp')
    
    @cached_property  
    def cnocr(self):
        return AlOcr(name='cnocr')
    
    @cached_property
    def jp(self):
        return AlOcr(name='jp')
    
    @cached_property
    def tw(self):
        return AlOcr(name='tw')

OCR_MODEL = OcrModel()
```

3. **Update `module/ocr/ocr.py`** to handle missing imports gracefully

### Step 3: Apply Python Modernization
1. Restore the stashed changes that already modernized the code
2. Fix the OCR modules with the Tesseract implementation
3. Update requirements to use Tesseract instead of cnocr

### Step 4: Create Migration Script
```python
# migrate_to_tesseract.py
import os
import subprocess
import sys

def install_tesseract():
    """Guide user through Tesseract installation"""
    print("=" * 60)
    print("ALAS OCR Migration to Tesseract")
    print("=" * 60)
    
    if sys.platform == "win32":
        print("\n1. Download Tesseract installer:")
        print("   https://github.com/UB-Mannheim/tesseract/wiki")
        print("\n2. Install to: C:\\Program Files\\Tesseract-OCR")
        print("\n3. Install language data during setup:")
        print("   - English (eng)")
        print("   - Japanese (jpn)")  
        print("   - Chinese Simplified (chi_sim)")
        print("   - Chinese Traditional (chi_tra)")
    else:
        print("\nInstall Tesseract:")
        print("  Ubuntu/Debian: sudo apt install tesseract-ocr tesseract-ocr-eng tesseract-ocr-jpn tesseract-ocr-chi-sim tesseract-ocr-chi-tra")
        print("  macOS: brew install tesseract tesseract-lang")
    
    print("\n4. Install Python package:")
    print("   pip install pytesseract pillow")
    
    input("\nPress Enter when Tesseract is installed...")

def test_tesseract():
    """Test if Tesseract is working"""
    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        print(f"✓ Tesseract {version} found")
        return True
    except:
        print("✗ Tesseract not found")
        return False

if __name__ == "__main__":
    if not test_tesseract():
        install_tesseract()
        if not test_tesseract():
            print("Please install Tesseract and try again")
            sys.exit(1)
    
    print("\n✓ Ready to use Tesseract OCR")
```

## Execution Order

1. **First**: Apply the Tesseract implementation
2. **Second**: Apply the stashed Python modernization 
3. **Third**: Update dependencies
4. **Fourth**: Test with actual game

## Dependencies to Change

### Remove:
- cnocr==1.2.2
- mxnet==1.6.0  
- gluoncv (dependency of cnocr)

### Add:
- pytesseract>=0.3.10
- Pillow>=10.0.0 (already present, update version)

## Expected Results

### What Will Work:
- Basic text recognition (with lower accuracy initially)
- Number recognition (high accuracy)
- Duration parsing (HH:MM:SS)
- Multi-language support

### What Needs Tuning:
- Game-specific fonts may need preprocessing
- Accuracy on stylized text
- Recognition speed (Tesseract is slower)
- Small text recognition

### Optimization Opportunities:
1. Custom preprocessing for game UI
2. Training Tesseract on game fonts
3. Caching frequent text patterns
4. Using different PSM modes per context

## Testing Plan
1. Create test screenshots from game
2. Compare old vs new accuracy
3. Tune preprocessing parameters
4. Optimize for specific use cases
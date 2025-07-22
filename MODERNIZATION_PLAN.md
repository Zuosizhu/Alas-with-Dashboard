# ALAS Modernization Plan: Python Upgrade with Tesseract OCR

## Overview

This plan outlines a comprehensive refactoring of the ALAS codebase to:
1. Upgrade to Python 3.10+ with modern syntax
2. Replace the custom `cnocr` OCR with Tesseract
3. Use Poetry for dependency management
4. Maintain full functionality throughout the process

## Current State Analysis

### OCR Implementation
- **Current**: Uses `cnocr` with custom trained models
- **Models**: Located in `./bin/cnocr_models/`
  - `azur_lane`: 99.43% accuracy on game text
  - `azur_lane_jp`: 99.38% accuracy for Japanese
  - `cnocr`: General Chinese OCR
  - `jp`: Japanese specific
  - `tw`: Traditional Chinese
- **Features**:
  - Alphabet whitelisting (e.g., only numbers for duration)
  - Pre-processing for specific text colors
  - Multi-language support
  - Server/client architecture for performance

### Key OCR Use Cases
1. **Commission Detection** (`module/commission/project.py`)
   - Commission names (multiple languages)
   - Duration times (HH:MM:SS format)
   - Suffixes (Roman numerals I-VI)
   - Status detection

2. **Research Projects** (`module/research/`)
   - Project names
   - Time remaining
   - Resource costs

3. **Shop Items** (`module/shop/`)
   - Item names
   - Prices
   - Quantities

4. **Combat Results**
   - MVP detection
   - Item drops
   - Experience gained

## Migration Strategy

### Phase 1: Create Tesseract Wrapper (Week 1)
1. **Install Tesseract**
   ```python
   # New file: module/ocr/tesseract_ocr.py
   import pytesseract
   from PIL import Image
   import numpy as np
   
   class TesseractOCR:
       def __init__(self, lang='eng'):
           self.lang = lang
           # Map ALAS languages to Tesseract
           self.lang_map = {
               'azur_lane': 'eng',
               'cnocr': 'chi_sim',
               'jp': 'jpn',
               'tw': 'chi_tra',
               'azur_lane_jp': 'jpn+eng'
           }
   ```

2. **Implement Compatibility Layer**
   - Match existing `AlOcr` interface
   - Support alphabet whitelisting
   - Implement pre-processing pipeline

### Phase 2: Parallel Implementation (Week 2)
1. **Add Tesseract alongside cnocr**
   ```python
   # module/ocr/ocr.py
   if State.deploy_config.UseTestesseract:
       from module.ocr.tesseract_ocr import TesseractModel as OCR_MODEL
   else:
       from module.ocr.models import OCR_MODEL
   ```

2. **Create configuration option**
   - Add `UseTestesseract` flag
   - Allow users to switch between implementations
   - Log performance metrics for comparison

### Phase 3: Optimize Tesseract (Week 3)
1. **Custom preprocessing for game text**
   ```python
   def preprocess_for_tesseract(image, text_color):
       # Enhance contrast
       # Remove background
       # Scale for better recognition
       return processed_image
   ```

2. **Language-specific configurations**
   - Custom Tesseract configs for each use case
   - Whitelist characters per context
   - Optimize for speed vs accuracy

### Phase 4: Python Modernization (Week 4)
1. **Apply automated tools**
   - Run Black for formatting
   - Use Ruff with `--fix` for syntax upgrades
   - Convert to f-strings

2. **Manual improvements**
   - Add type hints to public APIs
   - Update deprecated patterns
   - Fix any remaining string formatting

### Phase 5: Dependency Migration (Week 5)
1. **Create pyproject.toml**
   - Migrate from requirements.txt
   - Use Python 3.10+ features
   - Add development dependencies

2. **Remove cnocr dependencies**
   - Remove mxnet, gluoncv
   - Update documentation
   - Clean up model files

## Implementation Details

### 1. Tesseract OCR Class Structure
```python
# module/ocr/tesseract_ocr.py
from typing import List, Optional, Union
import pytesseract
import cv2
import numpy as np
from PIL import Image

class TesseractOCR:
    def __init__(self, lang: str = 'eng', 
                 whitelist: Optional[str] = None,
                 config: Optional[str] = None):
        self.lang = self._map_language(lang)
        self.whitelist = whitelist
        self.config = self._build_config(whitelist, config)
    
    def ocr(self, image: np.ndarray) -> str:
        """Main OCR method matching AlOcr interface"""
        # Preprocess
        processed = self._preprocess(image)
        
        # Run OCR
        text = pytesseract.image_to_string(
            processed, 
            lang=self.lang,
            config=self.config
        )
        
        # Post-process
        return self._postprocess(text)
    
    def ocr_for_single_line(self, image: np.ndarray) -> str:
        """Optimized for single line text"""
        config = f"{self.config} --psm 7"  # Single line mode
        return pytesseract.image_to_string(image, lang=self.lang, config=config)
```

### 2. Preprocessing Pipeline
```python
def preprocess_game_text(image: np.ndarray, 
                        text_color: tuple = (255, 255, 255),
                        threshold: int = 128) -> np.ndarray:
    """Preprocess game screenshots for better OCR"""
    # 1. Extract text by color
    mask = extract_color_mask(image, text_color, threshold)
    
    # 2. Remove noise
    kernel = np.ones((2,2), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    # 3. Scale up for better recognition
    scale_factor = 2
    width = int(mask.shape[1] * scale_factor)
    height = int(mask.shape[0] * scale_factor)
    mask = cv2.resize(mask, (width, height), interpolation=cv2.INTER_CUBIC)
    
    # 4. Add border
    mask = cv2.copyMakeBorder(mask, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=255)
    
    return mask
```

### 3. Context-Specific Configurations
```python
# OCR configurations for different contexts
OCR_CONFIGS = {
    'duration': {
        'whitelist': '0123456789:',
        'config': '--psm 7 -c tessedit_char_whitelist=0123456789:'
    },
    'commission_name': {
        'lang': 'eng+chi_sim',
        'config': '--psm 7'
    },
    'numbers_only': {
        'whitelist': '0123456789',
        'config': '--psm 8 -c tessedit_char_whitelist=0123456789'
    }
}
```

### 4. Migration Path for Each Module

#### Commission Module
```python
# Before (cnocr)
ocr = Ocr(button, lang='cnocr')
name = ocr.ocr(self.image)

# After (Tesseract)
ocr = Ocr(button, lang='cnocr', context='commission_name')
name = ocr.ocr(self.image)
```

#### Duration OCR
```python
# Before
ocr = Duration(button)
duration = ocr.ocr(self.image)

# After (with better preprocessing)
ocr = Duration(button, use_tesseract=True)
duration = ocr.ocr(self.image)
```

## Testing Strategy

### 1. Accuracy Testing
- Create test dataset from game screenshots
- Compare cnocr vs Tesseract accuracy
- Focus on critical text (commissions, durations)

### 2. Performance Testing
- Measure OCR speed for both implementations
- Profile memory usage
- Test with batch processing

### 3. Integration Testing
- Run full automation cycles
- Verify all features work with Tesseract
- Check edge cases (rotated text, low contrast)

## Rollback Plan
1. Keep cnocr implementation intact during migration
2. Use feature flag to switch implementations
3. Maintain both until Tesseract proven stable
4. Document any accuracy differences

## Success Criteria
1. ✅ Tesseract achieves >90% accuracy on critical text
2. ✅ No performance regression (< 2x slower)
3. ✅ All tests pass with new implementation
4. ✅ Python 3.10+ with modern syntax
5. ✅ Poetry-based dependency management
6. ✅ Clean removal of mxnet/cnocr dependencies

## Timeline
- **Week 1**: Tesseract wrapper implementation
- **Week 2**: Parallel testing with feature flag
- **Week 3**: Optimization and tuning
- **Week 4**: Python modernization
- **Week 5**: Dependency cleanup and documentation

## Next Steps
1. Install Tesseract and pytesseract
2. Create initial wrapper class
3. Test on sample images
4. Implement preprocessing pipeline
5. Begin module-by-module migration
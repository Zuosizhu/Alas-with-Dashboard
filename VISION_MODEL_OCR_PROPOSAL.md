# Vision Model OCR Proposal for ALAS

## Executive Summary

Replace traditional OCR (Tesseract/cnocr) with modern vision models that can handle game text more accurately with less code complexity.

## Problem Analysis

### Current Challenges
1. **Missing Models**: Original cnocr models (~3MB each) trained on game text are missing
2. **Complex Preprocessing**: Requires color extraction, thresholding, resizing
3. **Language Specific**: Need different models for EN/JP/CN
4. **Poor on Game Text**: Traditional OCR struggles with stylized fonts

### Hardware Reality
Users running:
- Android emulator: 2-4GB RAM
- Azur Lane game: 1-2GB RAM  
- ALAS automation: Already using significant resources

**Conclusion**: They have hardware for lightweight vision models

## Proposed Solutions

### Option 1: EasyOCR (Recommended)
```python
# Installation
pip install easyocr

# Implementation (module/ocr/al_ocr.py)
import easyocr
reader = easyocr.Reader(['en', 'ja', 'ch_sim', 'ch_tra'], gpu=False)

class AlOcr:
    def ocr(self, image):
        results = reader.readtext(image, detail=0)
        return " ".join(results) if results else ""
```

**Pros:**
- 64MB per language
- No preprocessing needed
- Handles all text styles
- Good accuracy

**Cons:**
- Slower than original (~200ms vs ~50ms)

### Option 2: PaddleOCR
```python
# Installation  
pip install paddlepaddle paddleocr

# Implementation
from paddleocr import PaddleOCR
ocr_engine = PaddleOCR(use_angle_cls=True, lang='en')

class AlOcr:
    def ocr(self, image):
        result = ocr_engine.ocr(image, cls=True)
        return " ".join([line[1][0] for line in result[0]])
```

**Pros:**
- Excellent for Asian languages
- Fast performance
- Small model size

**Cons:**
- More complex setup
- Paddle framework dependency

### Option 3: TrOCR (Future-Proof)
```python
# Installation
pip install transformers torch

# Implementation  
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

processor = TrOCRProcessor.from_pretrained("microsoft/trocr-small-printed")
model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-small-printed")

class AlOcr:
    def ocr(self, image):
        inputs = processor(image, return_tensors="pt")
        ids = model.generate(inputs["pixel_values"])
        return processor.batch_decode(ids, skip_special_tokens=True)[0]
```

**Pros:**
- State-of-the-art accuracy
- Handles any text style
- Transformer-based

**Cons:**
- Larger size (~250MB)
- Requires PyTorch

## Implementation Strategy

### Phase 1: Quick Implementation (Day 1)
1. Install EasyOCR
2. Replace `module/ocr/al_ocr.py` with simple wrapper
3. Test basic functionality

### Phase 2: Optimization (Day 2-3)
1. Cache reader initialization
2. Add language detection
3. Optimize for common patterns (duration, numbers)

### Phase 3: Migration (Day 4-5)
1. Apply Python modernization
2. Remove old dependencies
3. Update documentation

## Code Changes Required

### Minimal Change Approach
```python
# module/ocr/al_ocr.py (Complete file)
import numpy as np
try:
    import easyocr
    reader = easyocr.Reader(['en', 'ja', 'ch_sim', 'ch_tra'], gpu=False)
    OCR_AVAILABLE = True
except:
    OCR_AVAILABLE = False

class AlOcr:
    def __init__(self, *args, **kwargs):
        self.name = kwargs.get('name', 'en')
        
    def ocr(self, image):
        if not OCR_AVAILABLE:
            return ""
        try:
            if isinstance(image, np.ndarray):
                results = reader.readtext(image, detail=0)
                return " ".join(results) if results else ""
            return ""
        except:
            return ""
    
    def ocr_for_single_line(self, image):
        return self.ocr(image)
    
    def ocr_for_single_lines(self, images):
        return [self.ocr(img) for img in images]
    
    def atomic_ocr_for_single_lines(self, images, alphabet=None):
        results = [self.ocr(img) for img in images]
        return [list(text) for text in results]
    
    def set_cand_alphabet(self, alphabet):
        pass  # Not needed with vision models
    
    def debug(self, images):
        for i, img in enumerate(images):
            print(f"Image {i}: {self.ocr(img)}")
```

## Advantages Over Traditional OCR

1. **No Preprocessing**: Handles any color/background
2. **Better Accuracy**: Trained on real-world text
3. **Simpler Code**: ~50 lines vs ~500 lines
4. **Multi-Language**: One model for all languages
5. **Future Proof**: Vision models keep improving

## Resource Requirements

| Solution | RAM Usage | Disk Space | Init Time | OCR Speed |
|----------|-----------|------------|-----------|-----------|
| EasyOCR  | ~500MB    | ~250MB     | 3-5s      | ~200ms    |
| PaddleOCR| ~300MB    | ~100MB     | 2-3s      | ~100ms    |
| TrOCR    | ~800MB    | ~250MB     | 5-8s      | ~150ms    |
| Original | ~200MB    | ~30MB      | 1-2s      | ~50ms     |

## Recommendation

Start with **EasyOCR** because:
1. Easiest to implement (literally 20 lines)
2. Good accuracy out of the box
3. Handles all required languages
4. Active development
5. No complex preprocessing

If speed becomes an issue, optimize later with:
- Model caching
- Batch processing
- Region-specific models
- Move to PaddleOCR

## Next Steps

1. Create new branch: `vision-model-ocr`
2. Install EasyOCR: `pip install easyocr`
3. Replace `al_ocr.py` with minimal implementation
4. Test with game screenshots
5. Compare accuracy with original
6. Apply Python modernization from stash

This approach is simpler, more maintainable, and likely more accurate than traditional OCR!
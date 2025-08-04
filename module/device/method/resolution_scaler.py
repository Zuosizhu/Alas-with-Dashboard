"""
ALAS Resolution Scaler Plugin
Automatically downscales screenshots from 1920x1280 to 1280x720
and upscales touch coordinates from 1280x720 to 1920x1280
"""
import cv2
import numpy as np
from functools import wraps
from module.logger import logger


class ResolutionScaler:
    # Source resolution (device) 
    SOURCE_WIDTH = 1920
    SOURCE_HEIGHT = 1280

    # Target resolution (ALAS requirement)
    TARGET_WIDTH = 1280
    TARGET_HEIGHT = 720

    # Scaling factors
    SCALE_X = SOURCE_WIDTH / TARGET_WIDTH  # 1.5
    SCALE_Y = SOURCE_HEIGHT / TARGET_HEIGHT  # 1.778

    # Use uniform scaling to maintain aspect ratio
    SCALE_FACTOR = min(SCALE_X, SCALE_Y)  # 1.5

    # Actual scaled dimensions using uniform scaling
    SCALED_WIDTH = int(SOURCE_WIDTH / SCALE_FACTOR)  # 1280
    SCALED_HEIGHT = int(SOURCE_HEIGHT / SCALE_FACTOR)  # 853

    # Crop offset to get exact 1280x720
    CROP_TOP = (SCALED_HEIGHT - TARGET_HEIGHT) // 2  # 66
    CROP_BOTTOM = SCALED_HEIGHT - TARGET_HEIGHT - CROP_TOP  # 67

    @classmethod
    def is_scaling_needed(cls, image):
        """Check if image needs scaling"""
        if image is None:
            return False
        height, width = image.shape[:2]
        return width == cls.SOURCE_WIDTH and height == cls.SOURCE_HEIGHT

    @classmethod
    def downscale_screenshot(cls, image):
        """Downscale screenshot from 1920x1280 to 1280x720"""
        if not cls.is_scaling_needed(image):
            return image

        # First scale down uniformly to maintain aspect ratio
        scaled = cv2.resize(image, (cls.SCALED_WIDTH, cls.SCALED_HEIGHT),
                           interpolation=cv2.INTER_AREA)  # INTER_AREA is best for downscaling

        # Then crop to exact 1280x720
        cropped = scaled[cls.CROP_TOP:cls.SCALED_HEIGHT-cls.CROP_BOTTOM, :]

        return cropped

    @classmethod
    def upscale_coordinates(cls, x, y):
        """Upscale touch coordinates from 1280x720 to 1920x1280"""
        # First adjust for crop
        y_adjusted = y + cls.CROP_TOP

        # Then scale up  
        x_scaled = int(x * cls.SCALE_FACTOR)
        y_scaled = int(y_adjusted * cls.SCALE_FACTOR)

        # Ensure coordinates are within bounds
        x_scaled = min(max(0, x_scaled), cls.SOURCE_WIDTH - 1)
        y_scaled = min(max(0, y_scaled), cls.SOURCE_HEIGHT - 1)

        return x_scaled, y_scaled


def apply_resolution_scaling():
    """
    Apply resolution scaling patches to ALAS
    Call this function to enable resolution scaling
    """
    logger.info('Applying resolution scaling patches...')
    
    try:
        # Import the device class
        from module.device.device import Device
        
        # Store original screenshot method
        original_screenshot = Device.screenshot
        
        @wraps(original_screenshot)
        def screenshot_with_scaling(self, *args, **kwargs):
            # Call original screenshot method
            image = original_screenshot(self, *args, **kwargs)
            
            # Apply scaling if needed
            if ResolutionScaler.is_scaling_needed(image):
                # Log once per session
                if not hasattr(self, '_scaling_logged'):
                    logger.info(f'Screenshots: {ResolutionScaler.SOURCE_WIDTH}x{ResolutionScaler.SOURCE_HEIGHT} -> {ResolutionScaler.TARGET_WIDTH}x{ResolutionScaler.TARGET_HEIGHT}')
                    logger.info(f'Touch coords: {ResolutionScaler.TARGET_WIDTH}x{ResolutionScaler.TARGET_HEIGHT} -> {ResolutionScaler.SOURCE_WIDTH}x{ResolutionScaler.SOURCE_HEIGHT}')
                    self._scaling_logged = True
                
                image = ResolutionScaler.downscale_screenshot(image)
                # Mark that scaling is active
                self._resolution_scaler_active = True
            else:
                self._resolution_scaler_active = False
            
            return image
        
        # Replace the screenshot method
        Device.screenshot = screenshot_with_scaling
        
        # Store original click method 
        original_click = Device.click
        
        @wraps(original_click)
        def click_with_scaling(self, x, y, *args, **kwargs):
            # Check if scaling is active
            if getattr(self, '_resolution_scaler_active', False):
                x, y = ResolutionScaler.upscale_coordinates(x, y)
            
            return original_click(self, x, y, *args, **kwargs)
        
        # Replace the click method
        Device.click = click_with_scaling
        
        logger.info('Resolution scaling patches applied successfully')
        
    except Exception as e:
        logger.error(f'Failed to apply resolution scaling: {e}')
        raise

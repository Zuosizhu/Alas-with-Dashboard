"""
Vision and asset matching tools for ALAS.

Provides tools for detecting specific game assets (images) on screen,
which is critical for identifying states and objects that the
general page navigation graph doesn't cover.
"""

import os
import glob
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from module.base.template import Template
try:
    from ._context import get_context
except ImportError:
    # Backward-compatible import path when invoked as a top-level `tools` module.
    from tools._context import get_context

# Cache for loaded templates to avoid disk I/O on every call
_TEMPLATE_CACHE: Dict[str, Template] = {}

def _get_template(asset_name: str) -> Optional[Template]:
    """
    Load a template by name from the assets directory.
    Supports names like 'MAIN_GOTO_CAMPAIGN' (automatically finds extension)
    or relative paths like 'en/ui/MAIN_GOTO_CAMPAIGN.png'
    """
    if asset_name in _TEMPLATE_CACHE:
        return _TEMPLATE_CACHE[asset_name]

    # Try to find the file
    # 1. Exact path provided?
    if os.path.exists(asset_name):
        t = Template(file=asset_name)
        _TEMPLATE_CACHE[asset_name] = t
        return t

    # Name provided? Search in assets
    # We assume standard ALAS asset structure: assets/{lang}
    # But alas.json config determines the language.
    ctx = get_context()
    try:
        lang = ctx.config.Alas_General_Language  # e.g., 'en', 'zh-CN', 'ja-JP'
        # Normalize language name to folder name (en, cn, jp, tw)
        if 'en' in lang.lower(): lang = 'en'
        elif 'zh-cn' in lang.lower() or 'cn' in lang.lower(): lang = 'cn'
        elif 'ja-jp' in lang.lower() or 'jp' in lang.lower(): lang = 'jp'
        elif 'zh-tw' in lang.lower() or 'tw' in lang.lower(): lang = 'tw'
        else: lang = 'en'
    except AttributeError:
        lang = 'en'
    
    # Common search paths
    search_paths = [
        f"assets/{lang}/ui/{asset_name}.png",
        f"assets/{lang}/ui/{asset_name}.jpg",
        f"assets/{lang}/combat/{asset_name}.png",
        f"assets/{lang}/commission/{asset_name}.png",
        f"assets/{lang}/{asset_name}.png", # Direct asset path
        # Fallback to recursively searching the assets dir
    ]

    for path in search_paths:
        if os.path.exists(path):
            t = Template(file=path)
            _TEMPLATE_CACHE[asset_name] = t
            return t
    
    # Recursive search as last resort (expensive)
    for root, dirs, files in os.walk(f"assets/{lang}"):
        for file in files:
            if os.path.splitext(file)[0] == asset_name:
                full_path = os.path.join(root, file)
                t = Template(file=full_path)
                _TEMPLATE_CACHE[asset_name] = t
                return t

    return None

def list_assets(filter_text: str = "") -> Dict[str, Any]:
    """
    List available assets in the assets directory.
    Useful for finding the exact name of a button or icon.

    Args:
        filter_text: Optional text to filter results (case-insensitive)

    Returns:
        dict with keys:
            - success (bool)
            - assets (list[str]): List of asset names found
            - error (None)
    """
    try:
        ctx = get_context()
        try:
            lang = ctx.config.Alas_General_Language
            if 'en' in lang.lower(): lang = 'en'
            elif 'zh-cn' in lang.lower() or 'cn' in lang.lower(): lang = 'cn'
            elif 'ja-jp' in lang.lower() or 'jp' in lang.lower(): lang = 'jp'
            elif 'zh-tw' in lang.lower() or 'tw' in lang.lower(): lang = 'tw'
            else: lang = 'en'
        except AttributeError:
            lang = 'en'
            
        root_dir = f"assets/{lang}"
        
        assets = []
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                if file.endswith(('.png', '.jpg')):
                    name = os.path.splitext(file)[0]
                    if not filter_text or filter_text.lower() in name.lower():
                        # Return relative path for context, but name is usually enough for match()
                        rel_path = os.path.relpath(os.path.join(root, file), root_dir)
                        assets.append(f"{name} ({rel_path})")
        
        return {
            "success": True,
            "assets": sorted(assets)[:100], # Limit to 100 to avoid context flooding
            "total_found": len(assets),
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "assets": [],
            "error": f"Failed to list assets: {e}"
        }

def match_asset(asset_name: str, threshold: float = 0.85) -> Dict[str, Any]:
    """
    Check if a specific asset is visible on the current screen.

    Args:
        asset_name: Name of the asset (e.g. "MAIN_GOTO_CAMPAIGN")
        threshold: Similarity threshold (0.0 to 1.0, default 0.85)

    Returns:
        dict with keys:
            - success (bool): True if operation ran (even if no match)
            - found (bool): True if asset was found
            - similarity (float): Best match score
            - bounds (tuple|None): (x1, y1, x2, y2) of match
            - center (tuple|None): (x, y) center of match
            - error (str|None)
    """
    try:
        ctx = get_context()
        template = _get_template(asset_name)
        if not template:
            return {
                "success": False,
                "found": False,
                "error": f"Asset not found: {asset_name}"
            }

        # Take screenshot
        ctx.device.screenshot()
        image = ctx.device.image

        # Use Template's match logic
        # Template.match_result returns (similarity, Button)
        sim, button = template.match_result(image)
        
        found = sim > threshold
        
        return {
            "success": True,
            "found": found,
            "similarity": float(sim),
            "bounds": button.area if found else None,
            "center": button.button if found else None, # Alas Button.button is (x1, y1, x2, y2) usually? No, it's click area.
            # Actually Button.button is (x1,y1,x2,y2) click area.
            # Let's calculate center for convenience
            "click_point": ((button.button[0]+button.button[2])//2, (button.button[1]+button.button[3])//2) if found else None,
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "found": False,
            "error": f"Match failed: {e}"
        }

def click_asset(asset_name: str, threshold: float = 0.85) -> Dict[str, Any]:
    """
    Find and click an asset if it exists.

    Args:
        asset_name: Name of the asset
        threshold: Similarity threshold

    Returns:
        dict with keys:
            - success (bool): True if clicked
            - found (bool): True if asset was found
            - error (str|None)
    """
    try:
        # Re-use match logic
        match_res = match_asset(asset_name, threshold)
        if not match_res['success']:
            return match_res
        
        if not match_res['found']:
            return {
                "success": False,
                "found": False,
                "error": f"Asset '{asset_name}' not found (sim={match_res['similarity']:.2f})"
            }
        
        # Perform click
        ctx = get_context()
        x, y = match_res['click_point']
        ctx.device.click_adb(x, y)
        
        return {
            "success": True,
            "found": True,
            "clicked_at": (x, y),
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "found": False,
            "error": f"Click failed: {e}"
        }

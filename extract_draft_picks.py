# extract_draft_picks.py
"""Extract Future Draft Picks data from NBA 2K26 screenshots."""

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

import cv2
import numpy as np
import pytesseract
from pytesseract import TesseractNotFoundError

# =========================
# USER CONFIG (EDIT ONCE)
# =========================

# If `tesseract --version` works in CMD, leave this as None.
TESSERACT_CMD: Optional[str] = None

# ROI for columns on Future Draft Picks screenshot: (x, y, w, h)
# Screenshots are 1920x1080 resolution
YEAR_COL_ROI: Tuple[int, int, int, int] = (96, 272, 122, 658)
ROUND_COL_ROI: Tuple[int, int, int, int] = (223, 272, 115, 658)
PICK_COL_ROI: Tuple[int, int, int, int] = (340, 272, 99, 658)
PROTECTION_COL_ROI: Tuple[int, int, int, int] = (440, 272, 346, 658)
ORIGIN_COL_ROI: Tuple[int, int, int, int] = (793, 272, 145, 658)

# Paths
PROJECT_ROOT = Path(".")
INPUT_DIR = PROJECT_ROOT / "input_screenshots"
OUTPUT_DIR = PROJECT_ROOT / "output"
DRAFT_PICKS_FILE = OUTPUT_DIR / "draft_picks.json"
TEAMS_DRAFT_DIR = OUTPUT_DIR / "teams_draft_picks"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
DEBUG_DIR = OUTPUT_DIR / "debug_draft_picks"

# =========================
# Helpers
# =========================

def _ensure_tesseract() -> None:
    if TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    try:
        pytesseract.get_tesseract_version()
    except (TesseractNotFoundError, FileNotFoundError):
        print("ERROR: Tesseract not found. Install it or set TESSERACT_CMD.")
        exit(1)

def _load_manifest(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))

def _is_draft_picks_screen(img_bgr: np.ndarray) -> bool:
    """Check if screenshot is a Future Draft Picks screen by looking for header text."""
    # Extract wide header area to catch the text
    # Text appears in format like "WNBA FUTURE DRAFT PICKS" or "Association Future Draft Picks"
    header_roi = img_bgr[10:60, 100:700].copy()
    
    gray = cv2.cvtColor(header_roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    
    try:
        text = pytesseract.image_to_string(gray, config="--psm 6").strip().lower()
        # Look for key words that indicate draft picks screen
        if ("future" in text and ("draft" in text or "picks" in text)) or "future draft" in text:
            return True
    except:
        pass
    
    return False

def _extract_team_name(img_bgr: np.ndarray) -> str:
    """Extract team name from screenshot using OCR.
    Team name appears in upper right with logo (1920x1080 resolution).
    """
    # Try upper right area where team name + logo appears
    team_roi = img_bgr[15:85, 1620:1900].copy()
    
    gray = cv2.cvtColor(team_roi, cv2.COLOR_BGR2GRAY)
    if gray.mean() < 127:
        gray = cv2.bitwise_not(gray)
    
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    
    team_text = pytesseract.image_to_string(gray, config="--psm 6").strip()
    
    # Clean up
    team_text = re.sub(r'[^A-Za-z0-9\s]', '', team_text)
    team_text = re.sub(r'\s+', ' ', team_text).strip()
    
    # Extract team name (usually last significant word)
    words = [w for w in team_text.split() if len(w) > 3]
    if words:
        team_text = words[-1]
    
    return team_text if team_text else "Unknown"

def _crop_roi_bgr(img_bgr: np.ndarray, roi: Tuple[int, int, int, int]) -> np.ndarray:
    x, y, w, h = roi
    return img_bgr[y:y + h, x:x + w].copy()

def _save_debug(path: Path, img: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), img)

def _preprocess_for_line_detection(col_bgr: np.ndarray) -> np.ndarray:
    """Preprocess column image for text line detection."""
    gray = cv2.cvtColor(col_bgr, cv2.COLOR_BGR2GRAY)
    bw = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31, 12
    )
    bw = cv2.medianBlur(bw, 3)
    bw = cv2.dilate(bw, np.ones((2, 2), np.uint8), iterations=1)
    return bw

def _find_text_lines(binary: np.ndarray) -> List[Tuple[int, int]]:
    """Find text line boundaries in binary image."""
    h, w = binary.shape
    row_sum = binary.sum(axis=1) / (255.0 * w)
    smooth = np.convolve(row_sum, np.ones(9) / 9, mode="same")

    thr = max(0.02, float(np.percentile(smooth, 85)) * 0.25)
    in_text = smooth > thr

    lines: List[Tuple[int, int]] = []
    y = 0
    while y < h:
        if in_text[y]:
            y0 = y
            while y < h and in_text[y]:
                y += 1
            y1 = y
            if y1 - y0 >= 8:
                lines.append((y0, y1))
        else:
            y += 1
    return lines

def _prep_for_ocr(line_bgr: np.ndarray) -> np.ndarray:
    """Prepare text line for OCR."""
    gray = cv2.cvtColor(line_bgr, cv2.COLOR_BGR2GRAY)
    bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    bw = cv2.resize(bw, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
    bw = cv2.copyMakeBorder(bw, 14, 14, 14, 14, cv2.BORDER_CONSTANT, value=255)
    return bw

def _ocr_text(img_bw: np.ndarray, config: str = "--oem 1 --psm 7") -> str:
    """Run OCR on preprocessed image."""
    try:
        text = pytesseract.image_to_string(img_bw, config=config).strip()
        return text
    except:
        return ""

def _normalize_year(text: str) -> Optional[str]:
    """Normalize year text (e.g., '2028')."""
    text = text.strip()
    # Extract 4-digit year
    match = re.search(r'\b(20[2-9][0-9])\b', text)
    if match:
        return match.group(1)
    return None

def _normalize_round(text: str) -> Optional[str]:
    """Normalize round text (e.g., '1st', '2nd')."""
    text = text.strip().lower()
    if "1st" in text or "1" in text:
        return "1st"
    elif "2nd" in text or "2" in text:
        return "2nd"
    return None

def _normalize_pick(text: str) -> Optional[str]:
    """Normalize pick text (usually '--' or a number)."""
    text = text.strip()
    if "--" in text or text == "":
        return None
    # Extract number if present
    match = re.search(r'\b(\d+)\b', text)
    if match:
        return match.group(1)
    return None

def _normalize_protection(text: str) -> Optional[str]:
    """Normalize protection text."""
    text = text.strip()
    if not text or text in ["--", "None"]:
        return None
    # Clean up common OCR errors
    text = re.sub(r'\s+', ' ', text)
    return text

def _normalize_origin(text: str) -> Optional[str]:
    """Normalize origin (team name)."""
    text = text.strip()
    if not text or text in ["--"]:
        return None
    # Clean up
    text = re.sub(r'[^A-Za-z0-9\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text if text else None

# =========================
# Main
# =========================

def main() -> None:
    _ensure_tesseract()
    
    if not INPUT_DIR.exists():
        print(f"ERROR: {INPUT_DIR} does not exist.")
        return
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEAMS_DRAFT_DIR.mkdir(parents=True, exist_ok=True)
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    
    image_files = sorted(INPUT_DIR.glob("*.png")) + sorted(INPUT_DIR.glob("*.jpg"))
    if not image_files:
        print(f"No images found in {INPUT_DIR}")
        return
    
    manifest = _load_manifest(MANIFEST_PATH)
    processed_files = {entry["file"] for entry in manifest if entry.get("type") == "draft_picks" and entry.get("processed")}
    
    all_picks: List[Dict[str, Any]] = []
    picks_by_team: Dict[str, List[Dict[str, Any]]] = {}
    
    new_count = 0
    
    for img_path in image_files:
        if img_path.name in processed_files:
            print(f"> Skipping {img_path.name} (already processed)")
            continue
        
        print(f"\n{'='*60}")
        print(f"Processing: {img_path.name}")
        print('='*60)
        
        img_bgr = cv2.imread(str(img_path))
        if img_bgr is None:
            print(f"  ! Cannot read image")
            continue
        
        if not _is_draft_picks_screen(img_bgr):
            print(f"  > Not a draft picks screen")
            continue
        
        team_name = _extract_team_name(img_bgr)
        print(f"  Team: {team_name}")
        
        # Extract each column
        year_col = _crop_roi_bgr(img_bgr, YEAR_COL_ROI)
        round_col = _crop_roi_bgr(img_bgr, ROUND_COL_ROI)
        pick_col = _crop_roi_bgr(img_bgr, PICK_COL_ROI)
        protection_col = _crop_roi_bgr(img_bgr, PROTECTION_COL_ROI)
        origin_col = _crop_roi_bgr(img_bgr, ORIGIN_COL_ROI)
        
        # Save debug images
        _save_debug(DEBUG_DIR / f"{img_path.stem}_year.png", year_col)
        _save_debug(DEBUG_DIR / f"{img_path.stem}_round.png", round_col)
        _save_debug(DEBUG_DIR / f"{img_path.stem}_pick.png", pick_col)
        _save_debug(DEBUG_DIR / f"{img_path.stem}_protection.png", protection_col)
        _save_debug(DEBUG_DIR / f"{img_path.stem}_origin.png", origin_col)
        
        # Find text lines in year column (use as reference for all columns)
        year_bw = _preprocess_for_line_detection(year_col)
        lines = _find_text_lines(year_bw)
        
        print(f"  Found {len(lines)} draft pick lines")
        
        for idx, (y0, y1) in enumerate(lines, 1):
            # Extract each field
            year_line = year_col[y0:y1, :].copy()
            round_line = round_col[y0:y1, :].copy()
            pick_line = pick_col[y0:y1, :].copy()
            protection_line = protection_col[y0:y1, :].copy()
            origin_line = origin_col[y0:y1, :].copy()
            
            # OCR each field
            year_bw = _prep_for_ocr(year_line)
            round_bw = _prep_for_ocr(round_line)
            pick_bw = _prep_for_ocr(pick_line)
            protection_bw = _prep_for_ocr(protection_line)
            origin_bw = _prep_for_ocr(origin_line)
            
            year_text = _ocr_text(year_bw, "--psm 7")
            round_text = _ocr_text(round_bw, "--psm 7")
            pick_text = _ocr_text(pick_bw, "--psm 7")
            protection_text = _ocr_text(protection_bw, "--psm 7")
            origin_text = _ocr_text(origin_bw, "--psm 7")
            
            print(f"    Line {idx} raw OCR: year='{year_text}' round='{round_text}' pick='{pick_text}' protection='{protection_text}' origin='{origin_text}'")
            
            # Normalize
            year = _normalize_year(year_text)
            round_type = _normalize_round(round_text)
            pick = _normalize_pick(pick_text)
            protection = _normalize_protection(protection_text)
            origin = _normalize_origin(origin_text)
            
            if not year or not round_type:
                # Skip invalid lines
                continue
            
            pick_record = {
                "team": team_name,
                "year": year,
                "round": round_type,
                "pick": pick,
                "protection": protection,
                "origin": origin,
                "source": img_path.name,
            }
            
            all_picks.append(pick_record)
            
            if team_name not in picks_by_team:
                picks_by_team[team_name] = []
            picks_by_team[team_name].append(pick_record)
            
            print(f"    {idx}. {year} {round_type} - Origin: {origin or 'N/A'} - Protection: {protection or 'None'}")
        
        # Update manifest
        manifest.append({
            "file": img_path.name,
            "type": "draft_picks",
            "team": team_name,
            "processed": True,
        })
        new_count += 1
    
    # Save results
    if all_picks:
        DRAFT_PICKS_FILE.write_text(json.dumps(all_picks, indent=2), encoding="utf-8")
        print(f"\n+ Saved {len(all_picks)} draft picks to {DRAFT_PICKS_FILE}")
        
        # Save per-team files
        for team, picks in picks_by_team.items():
            team_file = TEAMS_DRAFT_DIR / f"{team}.json"
            team_file.write_text(json.dumps(picks, indent=2), encoding="utf-8")
            print(f"  + {team}: {len(picks)} picks -> {team_file}")
    
    if new_count > 0:
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"\n+ Processed {new_count} new draft picks screenshots")
    else:
        print("\nNo new draft picks screenshots to process.")

if __name__ == "__main__":
    main()

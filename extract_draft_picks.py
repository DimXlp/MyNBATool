# extract_draft_picks.py
"""Extract Future Draft Picks data from NBA 2K26 screenshots."""

from __future__ import annotations
import json
import re
import shutil
from datetime import datetime
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
# Protection column is wider and starts slightly left to capture center-aligned text
PROTECTION_COL_ROI: Tuple[int, int, int, int] = (420, 272, 380, 658)
ORIGIN_COL_ROI: Tuple[int, int, int, int] = (793, 272, 145, 658)

# Paths
PROJECT_ROOT = Path(".")
INPUT_DIR = PROJECT_ROOT / "input_screenshots"
OUTPUT_DIR = PROJECT_ROOT / "output"
DRAFT_PICKS_FILE = OUTPUT_DIR / "draft_picks.json"
TEAMS_DRAFT_DIR = OUTPUT_DIR / "teams_draft_picks"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
DEBUG_DIR = OUTPUT_DIR / "debug_draft_picks"
ARCHIVE_DIR = PROJECT_ROOT / "archived_screenshots"

# NBA Teams for origin validation
NBA_TEAMS = [
    "Hawks", "Celtics", "Nets", "Hornets", "Bulls", "Cavaliers", "Mavericks", "Nuggets",
    "Pistons", "Warriors", "Rockets", "Pacers", "Clippers", "Lakers", "Grizzlies", "Heat",
    "Bucks", "Timberwolves", "Pelicans", "Knicks", "Thunder", "Magic", "76ers", "Suns",
    "Trail Blazers", "Kings", "Spurs", "Raptors", "Jazz", "Wizards"
]

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

def _archive_processed_screenshots(processed_files: List[str], screenshot_type: str) -> int:
    """Move processed screenshots to dated archive folder.
    
    Args:
        processed_files: List of screenshot filenames that were processed
        screenshot_type: Type of screenshot (e.g., 'draft_picks', 'roster', 'contracts', 'standings')
    
    Returns:
        Number of files successfully archived
    """
    if not processed_files:
        return 0
    
    # Create archive directory with today's date
    date_str = datetime.now().strftime("%Y-%m-%d")
    archive_path = ARCHIVE_DIR / date_str / screenshot_type
    archive_path.mkdir(parents=True, exist_ok=True)
    
    archived_count = 0
    for filename in processed_files:
        source = INPUT_DIR / filename
        if source.exists():
            destination = archive_path / filename
            try:
                shutil.move(str(source), str(destination))
                archived_count += 1
            except Exception as e:
                print(f"Warning: Could not archive {filename}: {e}")
    
    return archived_count

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
    Team name appears just above the column headers (1920x1080 resolution).
    """
    # Team name appears just above column headers around Y 180-250
    team_roi = img_bgr[180:250, 50:900].copy()
    
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
    
    # Fix common OCR errors
    team_text = team_text.replace("Anicks", "Knicks")
    
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
    smooth = np.convolve(row_sum, np.ones(7) / 7, mode="same")

    # Lower threshold to catch more lines
    thr = max(0.01, float(np.percentile(smooth, 75)) * 0.2)
    in_text = smooth > thr

    lines: List[Tuple[int, int]] = []
    y = 0
    while y < h:
        if in_text[y]:
            y0 = y
            while y < h and in_text[y]:
                y += 1
            y1 = y
            # Accept smaller line heights
            if y1 - y0 >= 6:
                lines.append((y0, y1))
        else:
            y += 1
    return lines

def _prep_for_ocr(line_bgr: np.ndarray, is_protection: bool = False) -> np.ndarray:
    """Prepare text line for OCR."""
    gray = cv2.cvtColor(line_bgr, cv2.COLOR_BGR2GRAY)
    
    if is_protection:
        # Protection column needs special handling
        # First resize to make text larger
        gray = cv2.resize(gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
        # Use simple threshold instead of adaptive for cleaner results
        _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # Slight dilation to connect broken characters
        kernel = np.ones((2, 2), np.uint8)
        bw = cv2.dilate(bw, kernel, iterations=1)
    else:
        bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        bw = cv2.resize(bw, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
        # Additional cleanup for better OCR
        kernel = np.ones((2, 2), np.uint8)
        bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, kernel)
    
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
    """Normalize round text (e.g., '1st', '2nd').
    NBA only has 2 rounds, so we look for 1/2 or st/nd suffix.
    """
    text = text.strip().lower()
    
    # Look for "2" anywhere - if found, it's 2nd round
    # Common OCR errors: 2nd, znd, 2na, and
    if re.search(r'2', text) or "znd" in text or "2na" in text or "and" in text:
        return "2nd"
    
    # Look for "1" or 1st-like patterns
    if re.search(r'1', text) or "ist" in text or "lst" in text or "ict" in text or "det" in text:
        return "1st"
    
    # Look for suffix pattern: if ends with 'st' it's 1st, if ends with 'nd' it's 2nd  
    if text.endswith('st') or text.endswith('ct'):
        return "1st"
    elif text.endswith('nd') or text.endswith('na'):
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
    """Normalize protection text.
    Valid patterns: 'Swap Worst with [Team]', 'Swap Best with [Team]', 'Lottery Protected', or null.
    """
    text = text.strip()
    if not text or text in ["--", "None"]:
        return None
    
    text = re.sub(r'\s+', ' ', text)
    text_lower = text.lower()
    
    # Check for "Swap Worst with" pattern
    if "swap" in text_lower and "worst" in text_lower:
        # Extract team name after "with"
        match = re.search(r'with\s+([A-Za-z]+)', text, re.IGNORECASE)
        if match:
            team = _find_closest_team(match.group(1))
            if team:
                return f"Swap Worst with {team}"
        return text  # Return as-is if can't parse
    
    # Check for "Swap Best with" pattern
    if "swap" in text_lower and "best" in text_lower:
        # Extract team name after "with"
        match = re.search(r'with\s+([A-Za-z]+)', text, re.IGNORECASE)
        if match:
            team = _find_closest_team(match.group(1))
            if team:
                return f"Swap Best with {team}"
        return text  # Return as-is if can't parse
    
    # Check for "Lottery Protected"
    if "lottery" in text_lower and "protect" in text_lower:
        return "Lottery Protected"
    
    # Check for top-N protection pattern (e.g., "Top 10 Protected")
    match = re.search(r'top\s+(\d+)\s+protect', text_lower)
    if match:
        return f"Top {match.group(1)} Protected"
    
    # If it's gibberish (too many non-alpha characters or too many short words), return None
    alpha_chars = sum(c.isalpha() for c in text)
    if len(text) > 10 and alpha_chars / len(text) < 0.5:
        return None
    
    # Check if text has too many very short words (likely OCR garbage)
    words = text.split()
    if len(words) > 5:
        short_words = sum(1 for w in words if len(w) <= 2)
        if short_words / len(words) > 0.6:  # More than 60% are 1-2 letter words
            return None
    
    # If we got here and text doesn't match known patterns, it's likely OCR error
    # Only return it if it looks reasonably structured
    if len(text) > 15 and not any(keyword in text_lower for keyword in ['swap', 'lottery', 'protect', 'top']):
        return None
    
    return text

def _find_closest_team(text: str) -> Optional[str]:
    """Find closest matching NBA team name."""
    if not text:
        return None
    
    text = text.lower()
    # Direct match
    for team in NBA_TEAMS:
        if team.lower() in text or text in team.lower():
            return team
    
    # Common OCR errors
    corrections = {
        "buls": "Bulls",
        "bull": "Bulls",
        "pauls": "Bulls",  # OCR error
        "incts": "Bulls",  # OCR error for Bulls
        "inctsbus": "Bulls",  # OCR error for Bulls
        "lakers": "Lakers",
        "fakes": "Lakers",  # OCR error
        "takers": "Lakers",  # OCR error
        "knicks": "Knicks",
        "anicks": "Knicks",
        "nicks": "Knicks",  # OCR error
        "kicks": "Knicks",  # OCR error
        "kings": "Kings",
        "magic": "Magic",
        "maaic": "Magic",
        "iviagic": "Wizards",  # Common OCR error for Wizards
        "wizaras": "Wizards",  # OCR error
        "win": "Wizards",  # Fragment of Wizards
        "wiards": "Wizards",
        "nets": "Nets",
        "pelicans": "Pelicans",
        "pecans": "Pelicans",  # OCR error
        "pacers": "Pacers",
        "suns": "Suns",
        "jazz": "Jazz",
        "jez": "Jazz",  # OCR error
        "wizards": "Wizards",
        "vvizalgs": "Wizards",
        "wvizards": "Wizards",
        "grizzlies": "Grizzlies",
        "celtics": "Celtics",
        "attics": "Celtics",  # OCR error
        "cater": "Celtics",  # OCR error
        "heat": "Heat",
        "hawks": "Hawks",
        "pistons": "Pistons",
        "bucks": "Bucks",
        "cavaliers": "Cavaliers",
        "cavs": "Cavaliers",
        "mae": "Magic",  # OCR error
        "zane": "Suns",  # OCR error
        "foe": "76ers",  # OCR error
        "ses": "Suns",  # OCR error
    }
    
    for key, value in corrections.items():
        if key in text:
            return value
    
    # If no match found, return cleaned text
    return text.title() if len(text) > 2 else None

def _normalize_origin(text: str) -> Optional[str]:
    """Normalize origin (team name)."""
    text = text.strip()
    if not text or text in ["--"]:
        return None
    # Clean up
    text = re.sub(r'[^A-Za-z0-9\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Find closest NBA team
    return _find_closest_team(text)

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
    unprocessed_images = [img for img in image_files if img.name not in processed_files]
    
    if unprocessed_images:
        print(f"\nProcessing {len(unprocessed_images)} draft picks screenshot(s)...")
        print("=" * 60)
    
    for img_path in image_files:
        if img_path.name in processed_files:
            # print(f"> Skipping {img_path.name} (already processed)")
            continue
        
        # print(f"\n{'='*60}")
        # print(f"Processing: {img_path.name}")
        # print('='*60)
        
        img_bgr = cv2.imread(str(img_path))
        if img_bgr is None:
            # print(f"  ! Cannot read image")
            continue
        
        if not _is_draft_picks_screen(img_bgr):
            # print(f"  > Not a draft picks screen")
            continue
        
        team_name = _extract_team_name(img_bgr)
        # print(f"  Team: {team_name}")
        
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
        
        # Find text lines in both year and origin columns separately
        year_bw = _preprocess_for_line_detection(year_col)
        year_lines = _find_text_lines(year_bw)
        
        origin_bw = _preprocess_for_line_detection(origin_col)
        origin_lines = _find_text_lines(origin_bw)
        
        # print(f"  Found {len(year_lines)} draft pick lines in year column")
        # print(f"  Found {len(origin_lines)} text lines in origin column")
        
        # Pre-scan round column to find where each round marker appears (Y position)
        round_gray = cv2.cvtColor(round_col, cv2.COLOR_BGR2GRAY)
        round_gray_scaled = cv2.resize(round_gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        
        # Find all instances of "1st" and "2nd" with their Y positions
        round_markers = []  # List of (y_pos, round_type)
        
        # Search for "1st" and "2nd" text positions
        height = round_col.shape[0]
        step = 30  # Check every 30 pixels
        for y in range(0, height, step):
            snippet = round_gray[y:min(y+40, height), :]
            if snippet.shape[0] < 10:
                continue
            snippet_scaled = cv2.resize(snippet, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
            text = pytesseract.image_to_string(snippet_scaled, config="--psm 7").strip().lower()
            
            # Check what round this is
            round_val = _normalize_round(text)
            if round_val:
                round_markers.append((y, round_val))
        
        # print(f"  Round markers found: {round_markers}")
        
        # Use round markers to determine which lines belong to which round
        def get_round_for_line(y_pos):
            """Determine round based on Y position and round markers."""
            # Find the most recent round marker before this Y position
            applicable_round = "1st"  # Default to 1st
            for marker_y, marker_round in round_markers:
                if marker_y <= y_pos:
                    applicable_round = marker_round
                else:
                    break
            return applicable_round
        
        last_valid_round = None  # Track the last valid round for merged cells
        
        # Match each year line to the closest origin line
        for idx, (y0, y1) in enumerate(year_lines, 1):
            print(f"  Processing pick {idx}/{len(year_lines)}...")
            # Expand line boundaries to ensure we capture all text
            y0_expanded = max(0, y0 - 12)
            y1_expanded = min(year_col.shape[0], y1 + 12)
            
            # Extract each field with expanded boundaries from year column position
            year_line = year_col[y0_expanded:y1_expanded, :].copy()
            round_line = round_col[y0_expanded:y1_expanded, :].copy()
            pick_line = pick_col[y0_expanded:y1_expanded, :].copy()
            protection_line = protection_col[y0_expanded:y1_expanded, :].copy()
            
            # Find the origin line that's closest to this year line
            # Origin is center-aligned so text may be at different Y position
            year_center = (y0 + y1) // 2
            best_origin_line = None
            best_distance = float('inf')
            
            for orig_y0, orig_y1 in origin_lines:
                origin_center = (orig_y0 + orig_y1) // 2
                distance = abs(origin_center - year_center)
                # Only consider origin lines within 50 pixels of the year line
                if distance < 50 and distance < best_distance:
                    best_distance = distance
                    best_origin_line = (orig_y0, orig_y1)
            
            # Extract origin using its own line boundaries (or expanded year line if no match)
            if best_origin_line:
                orig_y0, orig_y1 = best_origin_line
                orig_y0_expanded = max(0, orig_y0 - 12)
                orig_y1_expanded = min(origin_col.shape[0], orig_y1 + 12)
                origin_line = origin_col[orig_y0_expanded:orig_y1_expanded, :].copy()
            else:
                # Fallback: use same boundaries as year line
                origin_line = origin_col[y0_expanded:y1_expanded, :].copy()
            
            # OCR each field
            year_bw = _prep_for_ocr(year_line)
            round_bw = _prep_for_ocr(round_line)
            pick_bw = _prep_for_ocr(pick_line)
            protection_bw = _prep_for_ocr(protection_line, is_protection=True)
            origin_bw = _prep_for_ocr(origin_line)
            
            year_text = _ocr_text(year_bw, "--psm 7")
            round_text = _ocr_text(round_bw, "--psm 7")
            pick_text = _ocr_text(pick_bw, "--psm 7")
            protection_text = _ocr_text(protection_bw, "--psm 6")
            
            # For origin, try multiple PSM modes and keep best result
            origin_texts = [
                _ocr_text(origin_bw, "--psm 7").strip(),  # Single line
                _ocr_text(origin_bw, "--psm 8").strip(),  # Single word
                _ocr_text(origin_bw, "--psm 6").strip(),  # Block of text
            ]
            # Choose the longest result that has alphabetic characters
            origin_text = ""
            for txt in origin_texts:
                if len(txt) > len(origin_text) and any(c.isalpha() for c in txt):
                    origin_text = txt
            
            # Debug: save origin lines that look wrong
            if year_text and ("swap" in protection_text.lower() or len(origin_text) < 4 or not any(c.isupper() for c in origin_text)):
                cv2.imwrite(str(DEBUG_DIR / f"{img_path.stem}_origin_line{idx}_{year_text}_debug.png"), origin_bw)
                # print(f"    DEBUG: Saved origin line {idx} for year {year_text}: '{origin_text}' (PSM results: {origin_texts})")
            
            # Debug: save problematic protection lines
            if "lottery" in protection_text.lower() or (year_text == "2028" and origin_text and "bull" in origin_text.lower()):
                cv2.imwrite(str(DEBUG_DIR / f"{img_path.stem}_prot_line{idx}_debug.png"), protection_bw)
                # print(f"    DEBUG: Saved protection line {idx} (contains lottery or Bulls): '{protection_text}'")
            
            # print(f"    Line {idx} raw OCR: year='{year_text}' round='{round_text}' pick='{pick_text}' protection='{protection_text[:30]}' origin='{origin_text}'")
            
            # Normalize
            year = _normalize_year(year_text)
            round_type = _normalize_round(round_text)
            pick = _normalize_pick(pick_text)
            protection = _normalize_protection(protection_text)
            origin = _normalize_origin(origin_text)
            
            # print(f"    Line {idx} normalized: year={year} round={round_type} (from '{round_text}')")
            
            # Skip header rows
            if year_text.upper() == "YEAR" or round_text.upper() == "ROUND":
                continue
            
            # Determine round: use OCR if available, otherwise use Y position
            if round_type:
                last_valid_round = round_type
            else:
                # Use Y position to determine round
                round_from_position = get_round_for_line(y0)
                if round_from_position:
                    round_type = round_from_position
                    last_valid_round = round_type
                elif year and last_valid_round:
                    # Fall back to previous round
                    round_type = last_valid_round
            
            if not year or not round_type:
                # Skip invalid lines
                continue
            
            # Default origin to team name if null (team owns their own pick)
            if not origin:
                origin = team_name
            
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
            
            # print(f"    {idx}. {year} {round_type} - Origin: {origin or 'N/A'} - Protection: {protection or 'None'}")
        
        # Update manifest
        manifest.append({
            "file": img_path.name,
            "type": "draft_picks",
            "team": team_name,
            "processed": True,
        })
        new_count += 1
        picks_in_screenshot = len([p for p in all_picks if p.get("source") == img_path.name])
        print(f" ✓ Found {picks_in_screenshot} draft picks (Total: {len(all_picks)} picks extracted)")
    
    # Save results
    if all_picks:
        DRAFT_PICKS_FILE.write_text(json.dumps(all_picks, indent=2), encoding="utf-8")
        
        # Count unique teams
        teams_processed = len(picks_by_team)
        
        # Save per-team files
        for team, picks in picks_by_team.items():
            team_file = TEAMS_DRAFT_DIR / f"{team}.json"
            team_file.write_text(json.dumps(picks, indent=2), encoding="utf-8")
        
        if new_count > 0:
            print("=" * 60)
            print(f"\nCompleted processing {new_count} screenshot(s)\n")
        
        # Print summary matching other extractors format
        print("\n" + "=" * 60)
        print("EXTRACTION SUMMARY")
        print("=" * 60)
        print(f"Screenshots processed:  {new_count}")
        print(f"Teams found:            {teams_processed}")
        print(f"Draft picks extracted:  {len(all_picks)}")
        print(f"\nFiles saved:")
        print(f"  • {DRAFT_PICKS_FILE}")
        print(f"  • {TEAMS_DRAFT_DIR}/ (team-specific files)")
    
    if new_count > 0:
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        
        # Archive processed screenshots
        processed_files_to_archive = [item["file"] for item in manifest if item.get("type") == "draft_picks" and item.get("processed")]
        if processed_files_to_archive:
            archived = _archive_processed_screenshots(processed_files_to_archive, "draft_picks")
            if archived > 0:
                print(f"\n✓ Archived {archived} screenshot(s) to {ARCHIVE_DIR / datetime.now().strftime('%Y-%m-%d') / 'draft_picks'}")
        
        print("=" * 60)
    # else:
        # print("\nNo new draft picks screenshots to process.")

if __name__ == "__main__":
    main()

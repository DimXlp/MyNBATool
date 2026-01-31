#!/usr/bin/env python3
"""Extract NBA 2K26 standings from TeamStandings screenshots."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

import numpy as np
import cv2
import pytesseract
from pytesseract import TesseractNotFoundError

# =========================
# USER CONFIG
# =========================

TESSERACT_CMD: Optional[str] = None

# ROIs for Standings screen - (x, y, width, height)
STANDINGS_RANK_COL_ROI: Tuple[int, int, int, int] = (77, 443, 75, 469)
STANDINGS_TEAM_COL_ROI: Tuple[int, int, int, int] = (221, 443, 291, 469)
STANDINGS_WL_COL_ROI: Tuple[int, int, int, int] = (506, 443, 108, 469)

# Paths
PROJECT_ROOT = Path(".")
INPUT_DIR = PROJECT_ROOT / "input_screenshots"
OUTPUT_DIR = PROJECT_ROOT / "output"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
DEBUG_DIR = OUTPUT_DIR / "debug_standings"

# =========================
# Helpers
# =========================

def _ensure_tesseract() -> None:
    if TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    try:
        _ = pytesseract.get_tesseract_version()
    except (TesseractNotFoundError, FileNotFoundError):
        print("\nERROR: Tesseract is not installed or not reachable.\n")
        print("Fix options:")
        print("1) Install Tesseract and ensure this works in CMD:")
        print("   tesseract --version\n")
        print("2) OR set TESSERACT_CMD in this file to your tesseract.exe path")
        raise

def _load_manifest(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"manifest.json not found at: {path.resolve()}")
    return json.loads(path.read_text(encoding="utf-8"))

def _crop_roi_bgr(img_bgr: np.ndarray, roi: Tuple[int, int, int, int]) -> np.ndarray:
    x, y, w, h = roi
    return img_bgr[y:y + h, x:x + w].copy()

def _save_debug(path: Path, img: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), img)

def _preprocess_for_line_detection(col_bgr: np.ndarray) -> np.ndarray:
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
    h, w = binary.shape
    row_sum = binary.sum(axis=1) / (255.0 * w)
    smooth = np.convolve(row_sum, np.ones(9) / 9, mode="same")

    thr = max(0.02, float(np.percentile(smooth, 85)) * 0.25)
    in_text = smooth > thr

    lines: List[Tuple[int, int]] = []
    y = 0
    while y < h:
        if not in_text[y]:
            y += 1
            continue
        y0 = y
        while y < h and in_text[y]:
            y += 1
        y1 = y
        if (y1 - y0) >= 10:
            pad = 4
            lines.append((max(0, y0 - pad), min(h, y1 + pad)))
    return lines

def _parse_standings_screen(img_bgr: np.ndarray, fname: str, args) -> List[Dict[str, Any]]:
    """Parse a standings screen to extract conference, rank, team name, and W-L record."""
    
    standings_teams = []
    
    # Detect conference - try OCR first
    conference_roi = img_bgr[285:310, 450:570].copy()
    conference_roi = cv2.resize(conference_roi, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    conference_gray = cv2.cvtColor(conference_roi, cv2.COLOR_BGR2GRAY)
    _, conference_bw = cv2.threshold(conference_gray, 127, 255, cv2.THRESH_BINARY)
    if conference_bw.mean() < 127:
        conference_bw = cv2.bitwise_not(conference_bw)
    conference_text = pytesseract.image_to_string(conference_bw, config="--psm 7").strip().upper()
    
    if args.debug:
        _save_debug(DEBUG_DIR / f"{Path(fname).stem}__conference_roi.png", conference_bw)
    
    screenshot_conference = "Western" if "WEST" in conference_text else "Eastern" if "EAST" in conference_text else None
    
    # Team-based conference lookup (fallback)
    western_teams_set = {
        "dallas mavericks", "los angeles lakers", "oklahoma city thunder", 
        "portland trail blazers", "new orleans pelicans", "san antonio spurs",
        "utah jazz", "sacramento kings", "minnesota timberwolves", 
        "los angeles clippers", "memphis grizzlies", "phoenix suns",
        "golden state warriors", "houston rockets", "denver nuggets"
    }
    
    # Try to extract power rank from the team detail card
    power_rank_roi = img_bgr[240:260, 550:650].copy()
    power_rank_text = pytesseract.image_to_string(power_rank_roi, config="--psm 7 -c tessedit_char_whitelist=0123456789thsrdnTPowerRak:").strip()
    power_rank_match = re.search(r'(\d{1,2})(?:st|nd|rd|th)?', power_rank_text)
    power_rank = int(power_rank_match.group(1)) if power_rank_match and 1 <= int(power_rank_match.group(1)) <= 30 else None
    
    # Crop the columns
    rankcol = _crop_roi_bgr(img_bgr, STANDINGS_RANK_COL_ROI)
    teamcol = _crop_roi_bgr(img_bgr, STANDINGS_TEAM_COL_ROI)
    wlcol = _crop_roi_bgr(img_bgr, STANDINGS_WL_COL_ROI)
    
    if args.debug:
        _save_debug(DEBUG_DIR / f"{Path(fname).stem}__standings_team.png", teamcol)
        _save_debug(DEBUG_DIR / f"{Path(fname).stem}__standings_rank.png", rankcol)
        _save_debug(DEBUG_DIR / f"{Path(fname).stem}__standings_wl.png", wlcol)
    
    # Detect text lines in team name column
    mask = _preprocess_for_line_detection(teamcol)
    bands = _find_text_lines(mask)
    
    for i, (y0, y1) in enumerate(bands):
        if y1 - y0 < 10:
            continue
        
        # Extract team name
        team_line = teamcol[y0:y1, :].copy()
        team_gray = cv2.cvtColor(team_line, cv2.COLOR_BGR2GRAY)
        team_bw = cv2.threshold(team_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        team_bw = cv2.resize(team_bw, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
        team_name = pytesseract.image_to_string(team_bw, config="--psm 7").strip()
        
        # Clean up team name
        team_name = re.sub(r'^[^A-Za-z]+', '', team_name)
        team_name = re.sub(r'[^A-Za-z0-9\s]', ' ', team_name)
        team_name = re.sub(r'\s+', ' ', team_name).strip()
        
        if not team_name or team_name.upper() in ["TEAM", "NAME"]:
            continue
        
        # Extract rank
        rank_line = rankcol[y0:y1, :].copy()
        rank_gray = cv2.cvtColor(rank_line, cv2.COLOR_BGR2GRAY)
        rank_bw = cv2.threshold(rank_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        if rank_bw.mean() < 127:
            rank_bw = cv2.bitwise_not(rank_bw)
        rank_bw = cv2.resize(rank_bw, None, fx=4.0, fy=4.0, interpolation=cv2.INTER_CUBIC)
        rank_bw = cv2.copyMakeBorder(rank_bw, 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=255)
        rank_text = pytesseract.image_to_string(rank_bw, config="--psm 7 -c tessedit_char_whitelist=0123456789").strip()
        rank_val = int(rank_text) if rank_text.isdigit() and 1 <= int(rank_text) <= 30 else None
        
        # Extract W-L record
        wl_line = wlcol[y0:y1, :].copy()
        wl_gray = cv2.cvtColor(wl_line, cv2.COLOR_BGR2GRAY)
        wl_bw = cv2.threshold(wl_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        if wl_bw.mean() < 127:
            wl_bw = cv2.bitwise_not(wl_bw)
        wl_bw = cv2.resize(wl_bw, None, fx=4.0, fy=4.0, interpolation=cv2.INTER_CUBIC)
        wl_bw = cv2.copyMakeBorder(wl_bw, 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=255)
        wl_text = pytesseract.image_to_string(wl_bw, config="--psm 7 -c tessedit_char_whitelist=0123456789-").strip()
        
        # Clean W-L format
        wl_match = re.search(r'(\d{1,2})\s*-\s*(\d{1,2})', wl_text)
        if wl_match:
            wl_text = f"{wl_match.group(1)}-{wl_match.group(2)}"
        elif not wl_text or wl_text == "-":
            wl_text = None
        
        # Determine conference
        team_check = team_name.lower()
        if team_check in western_teams_set:
            conference = "Western"
        else:
            conference = "Eastern"
        
        if screenshot_conference:
            conference = screenshot_conference
        
        if team_name and (rank_val or wl_text):
            standings_teams.append({
                "conference": conference,
                "rank": rank_val,
                "power_rank": power_rank,
                "team": team_name,
                "record": wl_text if wl_text else None,
                "source": fname
            })
    
    return standings_teams

# =========================
# Main
# =========================

def main() -> None:
    parser = argparse.ArgumentParser(description="Extract standings from NBA 2K26 TeamStandings screenshots")
    parser.add_argument("--debug", action="store_true", help="Save debug crops/lines")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    _ensure_tesseract()
    manifest = _load_manifest(MANIFEST_PATH)

    standings_entries = [m for m in manifest if m.get("screen_type") == "TeamStandings"]
    
    if not standings_entries:
        print("No TeamStandings screenshots found in output/manifest.json")
        return

    if args.debug:
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)

    unique_standings: Dict[str, Dict[str, Any]] = {}
    processed = 0

    for entry in standings_entries:
        fname = entry.get("file")
        if not fname:
            continue
        
        img_path = INPUT_DIR / fname
        if not img_path.exists():
            print(f"WARNING: missing screenshot in input_screenshots: {fname}")
            continue
        
        img_bgr = cv2.imread(str(img_path))
        if img_bgr is None:
            print(f"WARNING: could not read image: {fname}")
            continue
        
        standings_data = _parse_standings_screen(img_bgr, fname, args)
        
        # Merge duplicates from overlapping screenshots
        for team in standings_data:
            key = team["team"].lower()
            existing = unique_standings.get(key)
            
            if existing is None:
                unique_standings[key] = team
            else:
                merged = existing.copy()
                
                if team.get("rank") is not None and existing.get("rank") is None:
                    merged["rank"] = team["rank"]
                
                if team.get("power_rank") is not None and existing.get("power_rank") is None:
                    merged["power_rank"] = team["power_rank"]
                
                if team.get("record") is not None and existing.get("record") is None:
                    merged["record"] = team["record"]
                
                new_complete = int(team.get("rank") is not None) + int(team.get("record") is not None)
                old_complete = int(existing.get("rank") is not None) + int(existing.get("record") is not None)
                if new_complete > old_complete:
                    merged["source"] = fname
                
                unique_standings[key] = merged
        
        processed += 1
    
    # Convert to list and group by conference
    all_standings_list = list(unique_standings.values())
    
    # Separate by conference and sort each
    eastern_teams = sorted(
        [t for t in all_standings_list if t["conference"] == "Eastern"],
        key=lambda t: (t["rank"] is None, t["rank"] if t["rank"] is not None else 999)
    )
    western_teams = sorted(
        [t for t in all_standings_list if t["conference"] == "Western"],
        key=lambda t: (t["rank"] is None, t["rank"] if t["rank"] is not None else 999)
    )
    
    # Combine with Eastern first, then Western
    all_standings = eastern_teams + western_teams
    
    # Save standings data
    if all_standings:
        (OUTPUT_DIR / "standings.json").write_text(
            json.dumps(all_standings, indent=2),
            encoding="utf-8"
        )
        eastern_count = len([t for t in all_standings if t["conference"] == "Eastern"])
        western_count = len([t for t in all_standings if t["conference"] == "Western"])
        print(f"Standings teams extracted: {len(all_standings)} (Eastern: {eastern_count}, Western: {western_count})")
        print(f"Saved: {OUTPUT_DIR / 'standings.json'}")
    
    print(f"Total screenshots processed: {processed}")
    if args.debug:
        print(f"Debug images saved in: {DEBUG_DIR.resolve()}")

if __name__ == "__main__":
    main()

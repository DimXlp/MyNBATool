# extract_contracts.py
from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

import numpy as np
import cv2
import pytesseract
from pytesseract import TesseractNotFoundError


# =========================
# USER CONFIG (EDIT ONCE)
# =========================

# If `tesseract --version` works in CMD, leave this as None.
TESSERACT_CMD: Optional[str] = None

# ROI for columns on Contract Extensions screenshot: (x, y, w, h)
NAME_COL_ROI: Tuple[int, int, int, int] = (75, 482, 248, 488)
SALARY_COL_ROI: Tuple[int, int, int, int] = (855, 482, 128, 488)
OPTION_COL_ROI: Tuple[int, int, int, int] = (982, 482, 124, 488)
SIGN_COL_ROI: Tuple[int, int, int, int] = (1102, 482, 116, 488)
EXTENSION_COL_ROI: Tuple[int, int, int, int] = (1223, 482, 173, 488)
NTC_COL_ROI: Tuple[int, int, int, int] = (1395, 482, 115, 488)

# Trims inside NAME column crop to reduce icon interference
# For contracts, use minimal trim since we want to capture all players including injured
LEFT_TRIM_RATIO = 0.0  # Don't trim left side - we need to capture names with injury icons
RIGHT_TRIM_RATIO = 0.02

# Characters allowed for name OCR
NAME_WHITELIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.-' "

# Known OCR corrections for problematic names
# Format: "incorrect ocr" -> "correct name"
NAME_CORRECTIONS = {
    "d. oncic": "L. Doncic",
    "d oncic": "L. Doncic",
    "oncic": "Doncic",
}

# Paths
PROJECT_ROOT = Path(".")
INPUT_DIR = PROJECT_ROOT / "input_screenshots"
OUTPUT_DIR = PROJECT_ROOT / "output"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
DEBUG_DIR = OUTPUT_DIR / "debug_contracts"

# =========================
# Helpers
# =========================

@dataclass
class LineResult:
    file: str
    y0: int
    y1: int
    text: str
    conf: float

ROMAN_SET = {"I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"}

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
        print("2) OR set TESSERACT_CMD in extract_contracts.py to your tesseract.exe path")
        raise

def _load_manifest(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"manifest.json not found at: {path.resolve()}")
    return json.loads(path.read_text(encoding="utf-8"))

def _is_contract_screen(img_bgr: np.ndarray) -> bool:
    """Check if screenshot is a Contract Extensions screen by looking for header text."""
    # Extract header text area (top portion where "Association Contract Extensions" appears)
    header_roi = img_bgr[20:35, 200:520].copy()
    
    gray = cv2.cvtColor(header_roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    
    try:
        text = pytesseract.image_to_string(gray, config="--psm 7").strip().upper()
        # Look for keywords that indicate contract screen
        if "CONTRACT" in text or "ASSOCIATION" in text or "EXTENSION" in text:
            return True
    except:
        pass
    
    return False

def _extract_team_name(img_bgr: np.ndarray) -> str:
    """Extract team name from screenshot using OCR.
    Team name ROI: x=111, y=84, w=268, h=41
    """
    team_roi = img_bgr[84:125, 111:379].copy()
    
    gray = cv2.cvtColor(team_roi, cv2.COLOR_BGR2GRAY)
    if gray.mean() < 127:
        gray = cv2.bitwise_not(gray)
    
    gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    
    team_text = pytesseract.image_to_string(gray, config="--psm 7").strip()
    
    team_text = re.sub(r'[^A-Za-z0-9\s]', '', team_text)
    team_text = re.sub(r'\s+', ' ', team_text).strip()
    
    return team_text if team_text else "Unknown"

def _crop_roi_bgr(img_bgr: np.ndarray, roi: Tuple[int, int, int, int]) -> np.ndarray:
    x, y, w, h = roi
    return img_bgr[y:y + h, x:x + w].copy()

def _save_debug(path: Path, img: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), img)

def _normalize_name(s: str) -> str:
    """Normalize player name to canonical format."""
    s = (s or "").strip()
    
    # Apply known OCR corrections first (case-insensitive)
    s_lower = s.lower()
    for wrong, correct in NAME_CORRECTIONS.items():
        if wrong in s_lower:
            s = correct
            break
    
    s = s.replace("|", " ")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"([A-Za-z])\.([A-Za-z])", r"\1. \2", s)
    s = re.sub(r"^[\.\-'\s]+", "", s)
    s = re.sub(r"[^A-Za-z\.\-'\s]", "", s).strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"^([A-Za-z])\s*\.?\s*([A-Za-z])", r"\1. \2", s)
    s = re.sub(r"^l\.\s", "I. ", s)
    
    # Fix: Remove injury icon OCR artifacts like "c. s " before name
    s = re.sub(r"^[a-z]\.\s*[a-z]\.\s*", "", s, flags=re.IGNORECASE)
    s = s.strip()
    
    # Fix common OCR: lowercase first letter in last name → Capitalize
    # "J. lsaac" → "J. Isaac", "D. oncic" → "D. Oncic"
    s = re.sub(r"(\s)([a-z])([a-z]{2,})", lambda m: m.group(1) + m.group(2).upper() + m.group(3), s)
    
    s = re.sub(r"\b(JR|Jr|jr)\b\.?", "Jr.", s)
    s = re.sub(r"\b(SR|Sr|sr)\b\.?", "Sr.", s)
    s = re.sub(r"(Jr\.|Sr\.)", r" \1", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"^([A-Za-z])\s+([A-Za-z])", r"\1. \2", s)
    
    def _roman_fix(m: re.Match) -> str:
        return m.group(1).upper()
    
    s = re.sub(r"\b(i{1,3}|iv|v|vi{0,3}|ix|x)\b\.?", _roman_fix, s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _preprocess_for_line_detection(namecol_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(namecol_bgr, cv2.COLOR_BGR2GRAY)
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

def _prep_name_for_ocr(line_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(line_bgr, cv2.COLOR_BGR2GRAY)
    bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    bw = cv2.resize(bw, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
    bw = cv2.copyMakeBorder(bw, 14, 14, 14, 14, cv2.BORDER_CONSTANT, value=255)
    return bw

def _ocr_try_name_configs(img_bw: np.ndarray) -> List[Tuple[str, float, str]]:
    results: List[Tuple[str, float, str]] = []
    for psm in (7, 6, 11):
        config = f"--oem 1 --psm {psm} -c tessedit_char_whitelist={NAME_WHITELIST}"
        data = pytesseract.image_to_data(img_bw, config=config, output_type=pytesseract.Output.DICT)

        words: List[str] = []
        confs: List[float] = []

        for txt, conf in zip(data.get("text", []), data.get("conf", [])):
            txt = (txt or "").strip()
            if txt:
                words.append(txt)
            try:
                c = float(conf)
                if c >= 0:
                    confs.append(c)
            except Exception:
                pass

        text = _normalize_name(" ".join(words))
        text = re.sub(r"^([A-Z])\s+([A-Za-z])", r"\1. \2", text)
        avg_conf = float(np.mean(confs)) if confs else -1.0
        results.append((text, avg_conf, f"psm{psm}"))

    return results

def _score_candidate(text: str, conf: float) -> float:
    if not text:
        return -999.0
    t = text.strip()

    if t.upper().replace(" ", "") in {"NAME", "N.AME"}:
        return -999.0

    score = 0.0
    if re.fullmatch(r"[A-Za-z]\.\s?[A-Za-z][A-Za-z'\-]{1,}(?:\s+(?:Jr\.|Sr\.|I|II|III|IV|V|VI|VII|VIII|IX|X))?$", t):
        score += 10.0
    elif re.fullmatch(r"[A-Za-z][A-Za-z'\-]{2,}", t):
        score += 6.0
    else:
        score += 1.0

    if conf >= 0:
        score += min(conf / 10.0, 8.0)

    return score

def _ocr_best_name(line_bgr: np.ndarray) -> Tuple[str, float]:
    bw = _prep_name_for_ocr(line_bgr)
    trials = _ocr_try_name_configs(bw)

    best_text, best_conf = "", -1.0
    best_score = -999.0

    for text, conf, _tag in trials:
        sc = _score_candidate(text, conf)
        if sc > best_score:
            best_score = sc
            best_text = text
            best_conf = conf

    best_text = _normalize_name(best_text)
    best_text = re.sub(r"^([A-Za-z])[il]\.\s*", r"\1. ", best_text)

    return best_text, (best_conf if best_conf >= 0 else 0.0)

def _has_special_icon(line_bgr: np.ndarray) -> bool:
    """Detect if player has injury or other special icon.
    NOTE: This function is kept for reference but NOT used in contract extraction.
    All players should be included in contracts regardless of injury status.
    """
    h, w = line_bgr.shape[:2]
    if w < 40:
        return False
    
    icon_region = line_bgr[:, :40].copy()
    hsv = cv2.cvtColor(icon_region, cv2.COLOR_BGR2HSV)
    
    # Detect RED injury icon
    red_lower1 = np.array([0, 80, 80])
    red_upper1 = np.array([10, 255, 255])
    red_lower2 = np.array([170, 80, 80])
    red_upper2 = np.array([180, 255, 255])
    red_mask1 = cv2.inRange(hsv, red_lower1, red_upper1)
    red_mask2 = cv2.inRange(hsv, red_lower2, red_upper2)
    red_mask = cv2.bitwise_or(red_mask1, red_mask2)
    
    if cv2.countNonZero(red_mask) > 30:
        return True
    
    # Detect YELLOW injury icon (less severe injuries)
    yellow_lower = np.array([20, 80, 80])
    yellow_upper = np.array([35, 255, 255])
    yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
    
    if cv2.countNonZero(yellow_mask) > 30:
        return True
    
    return False

def _looks_like_player_name(text: str) -> bool:
    t = _normalize_name(text)
    t = re.sub(r"^([a-z])\.", lambda m: m.group(1).upper() + ".", t)

    # Fix: Remove injury icon OCR junk like "c. s " at the start
    t = re.sub(r"^[a-z]\.\s*[a-z]\.\?\s*", "", t, flags=re.IGNORECASE)
    t = t.strip()

    parts = t.split()
    if len(parts) < 2:
        return False

    first, last = parts[0], parts[1]

    if not re.fullmatch(r"[A-Z]\.?", first):
        return False

    # Fix: Allow lowercase first letter in last name (OCR often fails on first letter)
    # "lsaac" → "Isaac", "oncic" → "Doncic", "ibrahimovic" → "Ibrahimovic"
    if re.fullmatch(r"[a-z][A-Za-z'\-]{1,}", last):
        return True

    if not re.fullmatch(r"[A-Z][A-Za-z'\-]{1,}", last):
        return False

    if len(parts) == 2:
        return True

    suffix = parts[2]
    if suffix in {"Jr.", "Sr."} or suffix in ROMAN_SET:
        return True

    return False

def _prep_simple_for_ocr(line_bgr: np.ndarray) -> np.ndarray:
    """For text fields: simple Otsu + optional invert."""
    gray = cv2.cvtColor(line_bgr, cv2.COLOR_BGR2GRAY)
    bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    if bw.mean() < 127:
        bw = cv2.bitwise_not(bw)

    bw = cv2.medianBlur(bw, 3)
    return bw

def _ocr_text_simple(line_bgr: np.ndarray, config: str = "--oem 1 --psm 7") -> Tuple[str, float]:
    """OCR text with simple preprocessing."""
    bw = _prep_simple_for_ocr(line_bgr)
    bw = cv2.resize(bw, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    bw = cv2.copyMakeBorder(bw, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=255)
    
    data = pytesseract.image_to_data(bw, config=config, output_type=pytesseract.Output.DICT)

    words, confs = [], []
    for txt, conf in zip(data.get("text", []), data.get("conf", [])):
        txt = (txt or "").strip()
        if txt:
            words.append(txt)
        try:
            c = float(conf)
            if c >= 0:
                confs.append(c)
        except Exception:
            pass

    text = " ".join(words).strip()
    avg_conf = float(np.mean(confs)) if confs else 0.0
    return text, avg_conf

def _parse_salary(text: str) -> Optional[str]:
    """Parse salary text like '$40.54M' or '$2.46M'."""
    if not text:
        return None
    
    # Clean up common OCR errors
    text = text.replace("$", "").replace(",", "").replace("S", "").strip()
    
    # Look for pattern like "40.54M" or "2.46M" or "40.54 M"
    match = re.search(r"(\d+\.?\d*)\s*[MmN]", text, re.IGNORECASE)
    if match:
        amount = match.group(1)
        return f"${amount}M"
    
    # Try to find just numbers with decimal
    match = re.search(r"(\d+\.\d+)", text)
    if match:
        amount = match.group(1)
        return f"${amount}M"
    
    return None

def _parse_option(text: str) -> Optional[str]:
    """Parse option text like 'Player', 'Team', 'None', '2 Yr Team', etc."""
    if not text:
        return None
    
    text = text.strip().upper()
    
    # Common option values (case insensitive, partial match)
    if "PLAYER" in text or "PLAYFR" in text:
        return "Player"
    elif "TEAM" in text:
        # Check for "2 Yr Team" or "2 YrTeam"
        if re.search(r"2\s*YR", text, re.IGNORECASE):
            return "2 Yr Team"
        return "Team"
    elif "NONE" in text or "NONF" in text:
        return "None"
    
    return None

def _parse_sign_status(text: str) -> Optional[str]:
    """Parse signing status like '1yr +1', '4 yrs', '2 yrs +2', etc."""
    if not text:
        return None
    
    text = text.strip()
    
    # Pattern: "1yr +1", "2 yrs +1", "4 yrs"
    match = re.search(r"(\d+)\s*[Yy][Rr][Ss]?\s*(\+\s*\d+)?", text)
    if match:
        years = match.group(1)
        plus = match.group(2).replace(" ", "") if match.group(2) else ""
        
        # Normalize: "1yr" vs "2 yrs"
        yr_text = "yr" if years == "1" else "yrs"
        
        result = f"{years}{yr_text}"
        if plus:
            result += f" {plus}"
        
        return result
    
    return None

def _parse_extension(text: str) -> Optional[str]:
    """Parse extension text like 'Will Resign', 'Not Eligible', 'None'."""
    if not text:
        return None
    
    text = text.strip().upper()
    
    if "WILL" in text and "RESIGN" in text:
        return "Will Resign"
    elif "NOT" in text and "ELIGIBLE" in text:
        return "Not Eligible"
    elif "NONE" in text or "NONF" in text:
        return "None"
    
    return None

def _parse_ntc(text: str) -> Optional[str]:
    """Parse No Trade Clause: 'Yes' or 'No'."""
    if not text:
        return None
    
    text = text.strip().upper()
    
    # Be more lenient with Yes/No detection
    if "YES" in text or text == "Y" or "YFS" in text:
        return "Yes"
    elif "NO" in text or text == "N" or "N0" in text:
        return "No"
    
    return None

# =========================
# Main
# =========================

def main() -> None:
    parser = argparse.ArgumentParser(description="Extract contracts from NBA 2K26 Contract Extensions screenshots")
    parser.add_argument("--debug", action="store_true", help="Save debug crops/lines")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    _ensure_tesseract()
    manifest = _load_manifest(MANIFEST_PATH)

    # Look for contract screens
    contract_entries = [m for m in manifest if m.get("screen_type") == "ContractExtensions"]
    
    print(f"Found {len(contract_entries)} contract screenshots in manifest")
    
    if not contract_entries:
        print("No contract screenshots found in output/manifest.json")
        return

    if args.debug:
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    else:
        if DEBUG_DIR.exists():
            shutil.rmtree(DEBUG_DIR, ignore_errors=True)

    all_line_results: List[LineResult] = []
    unique_names: Dict[str, Dict[str, Any]] = {}
    unique_contracts: Dict[str, Dict[str, Any]] = {}
    teams_data: Dict[str, List[Dict[str, Any]]] = {}
    processed = 0

    # Process contract screenshots
    for entry in contract_entries:
        fname = entry.get("file")
        if not fname:
            continue

        img_path = INPUT_DIR / fname
        if not img_path.exists():
            print(f"WARNING: missing screenshot: {fname}")
            continue

        img_bgr = cv2.imread(str(img_path))
        if img_bgr is None:
            print(f"WARNING: could not read image: {fname}")
            continue
        
        # Extract team name
        team_name = _extract_team_name(img_bgr)

        namecol = _crop_roi_bgr(img_bgr, NAME_COL_ROI)
        salarycol = _crop_roi_bgr(img_bgr, SALARY_COL_ROI)
        optioncol = _crop_roi_bgr(img_bgr, OPTION_COL_ROI)
        signcol = _crop_roi_bgr(img_bgr, SIGN_COL_ROI)
        extensioncol = _crop_roi_bgr(img_bgr, EXTENSION_COL_ROI)
        ntccol = _crop_roi_bgr(img_bgr, NTC_COL_ROI)

        # Trim name column
        h, w, _ = namecol.shape
        lx = int(w * LEFT_TRIM_RATIO)
        rx = int(w * (1.0 - RIGHT_TRIM_RATIO))
        namecol_trim = namecol[:, lx:rx].copy()
        
        if args.debug:
            _save_debug(DEBUG_DIR / f"{Path(fname).stem}__namecol.png", namecol_trim)

        mask = _preprocess_for_line_detection(namecol_trim)
        bands = _find_text_lines(mask)

        if args.debug:
            _save_debug(DEBUG_DIR / f"{Path(fname).stem}__mask.png", mask)

        for i, (y0, y1) in enumerate(bands):
            line_bgr = namecol_trim[y0:y1, :].copy()

            if line_bgr.shape[0] < 14 or line_bgr.shape[1] < 60:
                continue

            # NOTE: For contracts, we DO NOT filter out injury icons
            # because injured players still have active contracts
            
            if args.debug:
                _save_debug(DEBUG_DIR / f"{Path(fname).stem}__line_{i:02d}.png", line_bgr)

            text, conf = _ocr_best_name(line_bgr)

            if args.debug and text:
                print(f"  OCR extracted: '{text}' (conf={conf:.1f})")

            if not text:
                if args.debug:
                    print(f"    → FILTERED: empty text")
                continue
            if text.upper().replace(" ", "") in {"NAME", "N.AME"}:
                if args.debug:
                    print(f"    → FILTERED: header text")
                continue

            if not _looks_like_player_name(text):
                if args.debug:
                    print(f"    → FILTERED: doesn't look like player name")
                continue

            all_line_results.append(LineResult(file=fname, y0=y0, y1=y1, text=text, conf=conf))

            key = text.lower()
            if key not in unique_names or conf > unique_names[key]["conf"]:
                unique_names[key] = {"name": text, "conf": conf, "best_from": fname}

            # Extract contract data - validate bounds for each column
            # All columns should have same height, but y0:y1 must be valid for each
            sal_h = salarycol.shape[0]
            name_h = namecol_trim.shape[0]
            
            if args.debug:
                print(f"  {text}: name_h={name_h}, sal_h={sal_h}, y0={y0}, y1={y1}")
            
            if y0 >= sal_h or y1 > sal_h or y0 < 0 or y1 <= y0:
                print(f"WARNING: Invalid line bounds for {text}: y0={y0}, y1={y1}, salary_height={sal_h}")
                continue
            
            salary_line = salarycol[y0:y1, :].copy()
            option_line = optioncol[y0:y1, :].copy()
            sign_line = signcol[y0:y1, :].copy()
            extension_line = extensioncol[y0:y1, :].copy()
            ntc_line = ntccol[y0:y1, :].copy()

            if args.debug:
                _save_debug(DEBUG_DIR / f"{Path(fname).stem}__line_{i:02d}_salary.png", salary_line)
                _save_debug(DEBUG_DIR / f"{Path(fname).stem}__line_{i:02d}_option.png", option_line)

            # OCR each field
            salary_txt, _ = _ocr_text_simple(salary_line)
            salary_val = _parse_salary(salary_txt)
            
            option_txt, _ = _ocr_text_simple(option_line)
            option_val = _parse_option(option_txt)
            
            sign_txt, _ = _ocr_text_simple(sign_line)
            sign_val = _parse_sign_status(sign_txt)
            
            extension_txt, _ = _ocr_text_simple(extension_line)
            extension_val = _parse_extension(extension_txt)
            
            ntc_txt, _ = _ocr_text_simple(ntc_line)
            ntc_val = _parse_ntc(ntc_txt)
            
            if args.debug:
                print(f"  {text}: SAL='{salary_txt}'->{salary_val} OPT='{option_txt}'->{option_val} SIGN='{sign_txt}'->{sign_val} EXT='{extension_txt}'->{extension_val} NTC='{ntc_txt}'->{ntc_val}")

            contract = {
                "name": text,
                "team": team_name,
                "salary": salary_val,
                "option": option_val,
                "sign": sign_val,
                "extension": extension_val,
                "ntc": ntc_val,
                "source": fname,
                "y0": y0,
                "y1": y1,
                "name_conf": round(conf, 2),
            }

            existing = unique_contracts.get(key)
            
            if existing is None:
                unique_contracts[key] = contract
            else:
                # Merge: keep non-null values, prefer new data if both non-null
                merged = existing.copy()
                
                for field in ["salary", "option", "sign", "extension", "ntc"]:
                    if contract.get(field) is not None:
                        merged[field] = contract[field]
                
                if conf > existing.get("name_conf", 0):
                    merged["name"] = text
                    merged["name_conf"] = round(conf, 2)
                
                unique_contracts[key] = merged

        processed += 1

    contract_names = sorted([v["name"] for v in unique_names.values()], key=lambda s: s.lower())
    raw_out = [
        {"file": r.file, "y0": r.y0, "y1": r.y1, "text": r.text, "conf": round(r.conf, 2)}
        for r in all_line_results
    ]
    contracts_list = sorted(unique_contracts.values(), key=lambda p: p["name"].lower())
    
    # Group contracts by team
    teams_data: Dict[str, List[Dict[str, Any]]] = {}
    for contract in contracts_list:
        team = contract.get("team", "Unknown")
        if team not in teams_data:
            teams_data[team] = []
        teams_data[team].append(contract)
    
    # Save combined contracts file
    (OUTPUT_DIR / "contracts.json").write_text(
        json.dumps(contracts_list, indent=2),
        encoding="utf-8"
    )
    
    # Save team-specific files
    teams_dir = OUTPUT_DIR / "teams_contracts"
    teams_dir.mkdir(exist_ok=True)
    
    for team_name, contracts in teams_data.items():
        safe_team_name = re.sub(r'[^A-Za-z0-9]', '_', team_name)
        team_file = teams_dir / f"{safe_team_name}.json"
        team_file.write_text(
            json.dumps({
                "team": team_name,
                "contracts": sorted(contracts, key=lambda p: p["name"].lower())
            }, indent=2),
            encoding="utf-8"
        )

    (OUTPUT_DIR / "contract_names.json").write_text(json.dumps(contract_names, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "contract_names_raw.json").write_text(json.dumps(raw_out, indent=2), encoding="utf-8")

    print(f"Total screenshots processed: {processed}")
    print(f"Unique names extracted: {len(contract_names)}")
    print(f"Teams processed: {len(teams_data)}")
    print(f"Saved: {OUTPUT_DIR / 'contract_names.json'}")
    print(f"Saved: {OUTPUT_DIR / 'contract_names_raw.json'}")
    print(f"Saved: {OUTPUT_DIR / 'contracts.json'} (combined)")
    print(f"Saved: {teams_dir} (team-specific files)")
    if args.debug:
        print(f"Debug images saved in: {DEBUG_DIR.resolve()}")

if __name__ == "__main__":
    main()

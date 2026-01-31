# extract_roster_names.py
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
# Otherwise set it to your tesseract.exe full path, e.g.:
# r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSERACT_CMD: Optional[str] = None

# ROI for the NAME column on a RosterViewer screenshot: (x, y, w, h)
# Must contain ONLY the yellow NAME column (including header is OK; we filter it).
NAME_COL_ROI: Tuple[int, int, int, int] = (78, 495, 254, 469)

# ROIs for other columns - using NAME_COL y/height with user-measured x/width
POS_COL_ROI: Tuple[int, int, int, int] = (340, 495, 70, 469)  # POS column
AGE_COL_ROI: Tuple[int, int, int, int] = (449, 495, 59, 469)  # AGE column (x and width from user)
RATING_COL_ROI: Tuple[int, int, int, int] = (563, 495, 58, 469)  # RATING column (wider capture)
IN_COL_ROI = (620, 495, 50, 469)  # IN column (starts after RATING)

# Trims inside NAME column crop to reduce icon interference.
LEFT_TRIM_RATIO = 0.02
RIGHT_TRIM_RATIO = 0.02

# Characters allowed for name OCR (roman numerals are letters)
NAME_WHITELIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.-' "

POS_TESS_CONFIG = "--oem 1 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ/"
NUM_TESS_CONFIG = "--oem 1 --psm 7 -c tessedit_char_whitelist=0123456789"
TESS_CONFIG_DIGITS = "--oem 1 --psm 7 -c tessedit_char_whitelist=0123456789"

# Paths
PROJECT_ROOT = Path(".")
INPUT_DIR = PROJECT_ROOT / "input_screenshots"
OUTPUT_DIR = PROJECT_ROOT / "output"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
DEBUG_DIR = OUTPUT_DIR / "debug_roster"

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

def _parse_in_delta(in_cell_bgr: np.ndarray) -> Optional[int]:
    """Parse the IN column to extract rating change delta.
    Returns: +N for increase (▲), -N for decrease (▼), None if no change.
    """
    h, w = in_cell_bgr.shape[:2]

    # Split: left side has arrow, right side has number
    arrow_roi = in_cell_bgr[:, :int(w * 0.50)].copy()
    num_roi   = in_cell_bgr[:, int(w * 0.55):].copy()

    # -------------------------
    # 1) Determine sign via COLOR: green = up (+), red = down (-)
    # -------------------------
    sign = 0
    
    # Convert to HSV for better color detection
    hsv = cv2.cvtColor(arrow_roi, cv2.COLOR_BGR2HSV)
    
    # Green range in HSV (upward arrow)
    green_lower = np.array([35, 50, 50])
    green_upper = np.array([85, 255, 255])
    green_mask = cv2.inRange(hsv, green_lower, green_upper)
    
    # Red range in HSV (downward arrow) - red wraps around, so two ranges
    red_lower1 = np.array([0, 50, 50])
    red_upper1 = np.array([10, 255, 255])
    red_lower2 = np.array([170, 50, 50])
    red_upper2 = np.array([180, 255, 255])
    red_mask1 = cv2.inRange(hsv, red_lower1, red_upper1)
    red_mask2 = cv2.inRange(hsv, red_lower2, red_upper2)
    red_mask = cv2.bitwise_or(red_mask1, red_mask2)
    
    green_pixels = cv2.countNonZero(green_mask)
    red_pixels = cv2.countNonZero(red_mask)
    
    # Require at least 50 pixels to be confident
    if green_pixels > max(50, red_pixels * 2):
        sign = +1
    elif red_pixels > max(50, green_pixels * 2):
        sign = -1
    
    # If color detection fails, try shape-based detection as fallback
    if sign == 0:
        g = cv2.cvtColor(arrow_roi, cv2.COLOR_BGR2GRAY)
        _, bw = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if bw.mean() < 127:
            bw = 255 - bw
        bw = cv2.medianBlur(bw, 3)
        
        cnts, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if cnts:
            c = max(cnts, key=cv2.contourArea)
            if cv2.contourArea(c) > 30:
                x, y, ww, hh = cv2.boundingRect(c)
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cy = M["m01"] / M["m00"]
                    mid = y + hh / 2.0
                    # ▲ centroid sits LOWER, ▼ centroid sits HIGHER
                    sign = +1 if cy > mid else -1

    # -------------------------
    # 2) OCR the delta number only (right side)
    # -------------------------
    if sign == 0:
        return None
    
    # Preprocess number region
    num_gray = cv2.cvtColor(num_roi, cv2.COLOR_BGR2GRAY)
    _, num_bw = cv2.threshold(num_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if num_bw.mean() < 127:
        num_bw = 255 - num_bw
    
    # Enlarge for better OCR
    num_bw = cv2.resize(num_bw, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    num_bw = cv2.copyMakeBorder(num_bw, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=255)

    txt = pytesseract.image_to_string(num_bw, config=NUM_TESS_CONFIG).strip()
    m = re.search(r"\d{1,2}", txt or "")
    n = int(m.group()) if m else 0

    if n == 0:
        return None

    # Return signed integer: +N or -N
    return sign * n

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
        print("2) OR set TESSERACT_CMD in extract_roster_names.py to your tesseract.exe path, e.g.:")
        print(r'   TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"')
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

def _normalize_name(s: str) -> str:
    """
    Try to turn OCR output into a canonical:
      "J. Brunson"
      "C. Porter Jr."
      "G. Hill II"
    """
    s = (s or "").strip()
    s = s.replace("|", " ")
    s = re.sub(r"\s+", " ", s)

    # Separate dot collisions: "Mi.Bridges" -> "Mi. Bridges"
    s = re.sub(r"([A-Za-z])\.([A-Za-z])", r"\1. \2", s)

    # Remove leading punctuation junk like ".Anunoby"
    s = re.sub(r"^[\.\-'\s]+", "", s)

    # Keep only allowed characters
    s = re.sub(r"[^A-Za-z\.\-'\s]", "", s).strip()
    s = re.sub(r"\s+", " ", s)

    # Fix missing dot after initial: "PDadiet" -> "P. Dadiet"
    s = re.sub(r"^([A-Za-z])\s*\.?\s*([A-Za-z])", r"\1. \2", s)

    # Common OCR: "l." instead of "I."
    s = re.sub(r"^l\.\s", "I. ", s)

    # --- Normalize suffix forms ---
    # JR / Jr / Jr. -> Jr.
    s = re.sub(r"\b(JR|Jr|jr)\b\.?", "Jr.", s)
    # SR / Sr / Sr. -> Sr.
    s = re.sub(r"\b(SR|Sr|sr)\b\.?", "Sr.", s)

    # Ensure a space before Jr./Sr. if OCR glued it
    s = re.sub(r"(Jr\.|Sr\.)", r" \1", s)
    s = re.sub(r"\s+", " ", s).strip()

    # If OCR returns "I Evans" (missing dot), normalize to "I. Evans"
    s = re.sub(r"^([A-Za-z])\s+([A-Za-z])", r"\1. \2", s)

    # Roman numerals: normalize to uppercase and remove any trailing dot
    def _roman_fix(m: re.Match) -> str:
        return m.group(1).upper()

    s = re.sub(r"\b(i{1,3}|iv|v|vi{0,3}|ix|x)\b\.?", _roman_fix, s, flags=re.IGNORECASE)

    # Clean double spaces again
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

    # Kill header reads
    if t.upper().replace(" ", "") in {"NAME", "N.AME"}:
        return -999.0

    score = 0.0
    # Prefer "X. Lastname" (+ optional suffix)
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

    # Normalize common OCR “Mi.” / “Ml.” into "M."
    best_text = re.sub(r"^([A-Za-z])[il]\.\s*", r"\1. ", best_text)

    return best_text, (best_conf if best_conf >= 0 else 0.0)

def _looks_like_player_name(text: str) -> bool:
    t = _normalize_name(text)

    # Uppercase the first initial if OCR returned lowercase
    t = re.sub(r"^([a-z])\.", lambda m: m.group(1).upper() + ".", t)

    parts = t.split()
    if len(parts) < 2:
        return False

    first, last = parts[0], parts[1]

    # Accept OCR missing the dot: "I Evans" or "I. Evans"
    if not re.fullmatch(r"[A-Z]\.?", first):
        return False

    # Last name must look like a real last name (kills "E. E", "A", etc.)
    if not re.fullmatch(r"[A-Z][A-Za-z'\-]{1,}", last):
        return False

    # If it's exactly 2 parts, it's valid (most players)
    if len(parts) == 2:
        return True

    # If it has 3+ parts, only allow known suffixes as the 3rd token
    suffix = parts[2]
    if suffix in {"Jr.", "Sr."}:
        return True
    if suffix in ROMAN_SET:
        return True

    # If there's an unexpected 3rd token, reject (usually OCR junk)
    return False

def _prep_simple_for_ocr(line_bgr: np.ndarray) -> np.ndarray:
    """For POS/AGE/OVR: simple Otsu + (optional) invert."""
    gray = cv2.cvtColor(line_bgr, cv2.COLOR_BGR2GRAY)
    bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    # Ensure black text on white background
    if bw.mean() < 127:
        bw = cv2.bitwise_not(bw)

    bw = cv2.medianBlur(bw, 3)
    return bw


def _ocr_text_config(line_bgr: np.ndarray, config: str) -> Tuple[str, float]:
    bw = _prep_simple_for_ocr(line_bgr)
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


def _ocr_int_config(line_bgr: np.ndarray, debug_name: str = "") -> Tuple[Optional[int], float]:
    # Multiple OCR strategies - try simple approaches first
    gray = cv2.cvtColor(line_bgr, cv2.COLOR_BGR2GRAY)
    
    results = []
    all_attempts = []  # Track all OCR attempts for debugging
    partial_digits = []  # Track single digits that might be part of a 2-digit number
    
    # Strategy 1: Direct OCR on grayscale (enlarged)
    gray_large = cv2.resize(gray, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    gray_large = cv2.copyMakeBorder(gray_large, 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=0)
    try:
        text = pytesseract.image_to_string(gray_large, config=NUM_TESS_CONFIG).strip()
        all_attempts.append(f"gray: '{text}'")
        m = re.search(r"\d{1,3}", text)
        if m:
            num = int(m.group(0))
            # For OVR: Accept 10-19 temporarily (will be fixed later to 70-79)
            if "OVR" in debug_name and 10 <= num <= 99:
                results.append((num, 60.0))
            elif "AGE" in debug_name and 18 <= num <= 45:
                results.append((num, 60.0))
            elif "AGE" not in debug_name and "OVR" not in debug_name and ((18 <= num <= 45) or (60 <= num <= 99)):
                results.append((num, 60.0))  # Fallback for unknown type
            elif len(m.group(0)) == 1:  # Single digit - might be partial
                partial_digits.append(num)
    except Exception as e:
        all_attempts.append(f"gray: ERROR {e}")
    
    # Strategy 2: Inverted grayscale
    gray_inv = cv2.bitwise_not(gray_large)
    try:
        text = pytesseract.image_to_string(gray_inv, config=NUM_TESS_CONFIG).strip()
        all_attempts.append(f"gray_inv: '{text}'")
        m = re.search(r"\d{1,3}", text)
        if m:
            num = int(m.group(0))
            # For OVR: Accept 10-19 temporarily (will be fixed later to 70-79)
            if "OVR" in debug_name and 10 <= num <= 99:
                results.append((num, 60.0))
            elif "AGE" in debug_name and 18 <= num <= 45:
                results.append((num, 60.0))
            elif "AGE" not in debug_name and "OVR" not in debug_name and ((18 <= num <= 45) or (60 <= num <= 99)):
                results.append((num, 60.0))  # Fallback for unknown type
            elif len(m.group(0)) == 1:
                partial_digits.append(num)
    except Exception as e:
        all_attempts.append(f"gray_inv: ERROR {e}")
    
    # Strategy 3-5: Different thresholding methods
    for idx, thresh_method in enumerate([(0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU),
                                          (127, 255, cv2.THRESH_BINARY),
                                          (None, None, None)]):  # Adaptive
        if thresh_method[2] is None:
            bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 11, 2)
            method_name = "adaptive"
        else:
            _, bw = cv2.threshold(gray, thresh_method[0], thresh_method[1], thresh_method[2])
            method_name = f"thresh{idx}"
        
        bw = cv2.medianBlur(bw, 3)
        bw_large = cv2.resize(bw, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
        bw_large = cv2.copyMakeBorder(bw_large, 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=255)
        
        for invert_idx, img in enumerate([bw_large, cv2.bitwise_not(bw_large)]):
            try:
                text = pytesseract.image_to_string(img, config=NUM_TESS_CONFIG).strip()
                inv_str = "_inv" if invert_idx == 1 else ""
                all_attempts.append(f"{method_name}{inv_str}: '{text}'")
                m = re.search(r"\d{1,3}", text)
                if m:
                    num = int(m.group(0))
                    # For OVR: Accept 10-19 temporarily (will be fixed later to 70-79)
                    is_valid = False
                    if "OVR" in debug_name and 10 <= num <= 99:
                        is_valid = True
                    elif "AGE" in debug_name and 18 <= num <= 45:
                        is_valid = True
                    elif "AGE" not in debug_name and "OVR" not in debug_name and ((18 <= num <= 45) or (60 <= num <= 99)):
                        is_valid = True  # Fallback for unknown type
                    
                    if is_valid:
                        # Try to get confidence
                        data = pytesseract.image_to_data(img, config=NUM_TESS_CONFIG,
                                                         output_type=pytesseract.Output.DICT)
                        confs = [float(c) for c in data.get("conf", []) if c != -1]
                        conf = float(np.mean(confs)) if confs else 50.0
                        results.append((num, conf))
                    elif len(m.group(0)) == 1:
                        partial_digits.append(num)
            except Exception as e:
                inv_str = "_inv" if invert_idx == 1 else ""
                all_attempts.append(f"{method_name}{inv_str}: ERROR {e}")
    
    # Domain knowledge: Fix common OCR errors based on valid ranges
    # NBA 2K26 ratings: 60-99 (mostly 70-99), Ages: 18-45 (mostly 20-40)
    
    # SMART FIX: If rating reads as 10-19, it's missing the leading '7' → convert to 70-79
    if "OVR" in debug_name and results:
        fixed_results = []
        for num, conf in results:
            if 10 <= num <= 19:
                # OCR read "18" but it's actually "78", "19" → "79", etc.
                corrected = 70 + (num % 10)
                fixed_results.append((corrected, conf * 0.9))  # Slightly lower confidence
                if debug_name:
                    print(f"  Fixed {debug_name}: OCR read '{num}' -> corrected to '{corrected}'")
            else:
                fixed_results.append((num, conf))
        results = fixed_results
    
    # If we got no valid results but have partial digits, try to construct valid numbers
    if not results and partial_digits:
        # For AGE: common pattern is 2X (20-29), 3X (30-39), also 18-19
        # For OVR: common pattern is 7X (70-79), 8X (80-89), 9X (90-99)
        for digit in set(partial_digits):  # Remove duplicates
            if "AGE" in debug_name:
                # Special case: single digit 8 or 9 could be 18, 19, 28, 29, 38, 39
                if digit in [8, 9]:
                    for age in [10 + digit, 20 + digit, 30 + digit]:
                        if 18 <= age <= 45:
                            results.append((age, 35.0))
                else:
                    # Try 2X and 3X for other digits
                    for tens in [2, 3]:
                        candidate = tens * 10 + digit
                        if 20 <= candidate <= 39:
                            results.append((candidate, 40.0))  # Lower confidence
            elif "OVR" in debug_name:
                # Try 7X, 8X, 9X for ratings (NBA players rarely below 70)
                for tens in [7, 8, 9]:
                    candidate = tens * 10 + digit
                    if 70 <= candidate <= 99:
                        results.append((candidate, 40.0))  # Lower confidence
    
    # If we got no valid results, log what we tried
    if not results and debug_name:
        partial_str = f" (partials: {partial_digits})" if partial_digits else ""
        print(f"  OCR failed for {debug_name}{partial_str}: {'; '.join(all_attempts[:3])}")
    
    if not results:
        return None, 0.0
    
    # Return result with highest confidence
    return max(results, key=lambda x: x[1])

# =========================
# Main
# =========================

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Save debug crops/lines")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if NAME_COL_ROI == (0, 0, 0, 0):
        raise ValueError(
            "NAME_COL_ROI is not set.\n"
            "Edit extract_roster_names.py and set NAME_COL_ROI = (x, y, w, h)."
        )

    _ensure_tesseract()
    manifest = _load_manifest(MANIFEST_PATH)

    roster_entries = [m for m in manifest if m.get("screen_type") == "RosterViewer"]
    if not roster_entries:
        print("No RosterViewer screenshots found in output/manifest.json")
        return

    if args.debug:
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    else:
        if DEBUG_DIR.exists():
            shutil.rmtree(DEBUG_DIR, ignore_errors=True)

    all_line_results: List[LineResult] = []
    unique_names: Dict[str, Dict[str, Any]] = {}
    unique_players: Dict[str, Dict[str, Any]] = {}
    processed = 0

    def filled_count(p: dict) -> int:
        return int(p.get("pos") is not None) + int(p.get("age") is not None) + int(p.get("ovr") is not None)

    for entry in roster_entries:
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

        namecol = _crop_roi_bgr(img_bgr, NAME_COL_ROI)
        poscol = _crop_roi_bgr(img_bgr, POS_COL_ROI)
        agecol = _crop_roi_bgr(img_bgr, AGE_COL_ROI)
        ratingcol = _crop_roi_bgr(img_bgr, RATING_COL_ROI)
        incol = _crop_roi_bgr(img_bgr, IN_COL_ROI)

        # Trim left/right slightly to avoid icons
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

            if args.debug:
                _save_debug(DEBUG_DIR / f"{Path(fname).stem}__line_{i:02d}.png", line_bgr)

            text, conf = _ocr_best_name(line_bgr)

            # Filter header / empty / obvious junk
            if not text:
                continue
            if text.upper().replace(" ", "") in {"NAME", "N.AME"}:
                continue

            if not _looks_like_player_name(text):
                continue

            all_line_results.append(LineResult(file=fname, y0=y0, y1=y1, text=text, conf=conf))

            key = text.lower()
            if key not in unique_names or conf > unique_names[key]["conf"]:
                unique_names[key] = {"name": text, "conf": conf, "best_from": fname}

            # Debug: Track duplicate name detections
            if key in unique_players:
                print(f"  >> Processing {text} again from {fname} (y={y0}-{y1})")

            pos_line = poscol[y0:y1, :].copy()
            age_line = agecol[y0:y1, :].copy()
            ovr_line = ratingcol[y0:y1, :].copy()
            in_line  = incol[y0:y1, :].copy()

            if args.debug:
                _save_debug(DEBUG_DIR / f"{Path(fname).stem}__line_{i:02d}_age.png", age_line)
                _save_debug(DEBUG_DIR / f"{Path(fname).stem}__line_{i:02d}_ovr.png", ovr_line)

            pos_txt, _pos_conf = _ocr_text_config(pos_line, POS_TESS_CONFIG)
            pos_txt = pos_txt.upper().replace(" ", "")    

            valid_pos = {"PG", "SG", "SF", "PF", "C"}
            pos = next((p for p in valid_pos if p in pos_txt), None)        
            
            age_val, _age_conf = _ocr_int_config(age_line, f"{text} AGE")
            ovr_val, _ovr_conf = _ocr_int_config(ovr_line, f"{text} OVR")

            in_delta = _parse_in_delta(in_line)  # +1 / -2 / None

            player = {
                "name": text,
                "pos": pos,
                "age": age_val,
                "ovr": ovr_val,
                "in_delta": in_delta,
                "in_str": (f"{in_delta:+d}" if in_delta is not None else None),  # "+1" / "-2" / None
                "source": fname,
                "y0": y0,
                "y1": y1,
                "name_conf": round(conf, 2),
            }

            existing = unique_players.get(key)
            
            # Smart merge strategy for overlapping screenshots:
            # - If new player, add it
            # - If duplicate, MERGE: keep best value for EACH field (don't let nulls overwrite valid data)
            if existing is None:
                # New player, just add
                unique_players[key] = player
            else:
                # Duplicate player - merge by keeping best data for each field
                merged = existing.copy()
                
                # Update each field only if new value is better (non-null when existing is null, or both non-null but new has higher confidence)
                if player.get("pos") is not None and existing.get("pos") is None:
                    merged["pos"] = player["pos"]
                
                if player.get("age") is not None and existing.get("age") is None:
                    merged["age"] = player["age"]
                
                if player.get("ovr") is not None and existing.get("ovr") is None:
                    merged["ovr"] = player["ovr"]
                    print(f"  {text}: Added missing OVR={player['ovr']} from {fname}")
                
                if player.get("in_delta") is not None and existing.get("in_delta") is None:
                    merged["in_delta"] = player["in_delta"]
                    merged["in_str"] = player["in_str"]
                
                # Update source if we got more complete data
                new_filled = int(player.get("pos") is not None) + int(player.get("age") is not None) + int(player.get("ovr") is not None)
                old_filled = int(existing.get("pos") is not None) + int(existing.get("age") is not None) + int(existing.get("ovr") is not None)
                if new_filled > old_filled:
                    merged["source"] = fname
                    merged["y0"] = y0
                    merged["y1"] = y1
                
                # Keep higher name confidence
                if conf > existing.get("name_conf", 0):
                    merged["name"] = text  # Use better OCR'd name
                    merged["name_conf"] = round(conf, 2)
                
                unique_players[key] = merged

        processed += 1

    roster_names = sorted([v["name"] for v in unique_names.values()], key=lambda s: s.lower())
    raw_out = [
        {"file": r.file, "y0": r.y0, "y1": r.y1, "text": r.text, "conf": round(r.conf, 2)}
        for r in all_line_results
    ]
    roster_players = sorted(unique_players.values(), key=lambda p: p["name"].lower())
    (OUTPUT_DIR / "roster_players.json").write_text(
        json.dumps(roster_players, indent=2),
        encoding="utf-8"
    )

    (OUTPUT_DIR / "roster_names.json").write_text(json.dumps(roster_names, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "roster_names_raw.json").write_text(json.dumps(raw_out, indent=2), encoding="utf-8")

    print(f"Roster screenshots processed: {processed}")
    print(f"Unique names extracted: {len(roster_names)}")
    print(f"Saved: {OUTPUT_DIR / 'roster_names.json'}")
    print(f"Saved: {OUTPUT_DIR / 'roster_names_raw.json'}")
    print(f"Saved: {OUTPUT_DIR / 'roster_players.json'}")
    if args.debug:
        print(f"Debug images saved in: {DEBUG_DIR.resolve()}")

if __name__ == "__main__":
    main()

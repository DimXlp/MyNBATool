import json
import re
from pathlib import Path

import cv2
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# =========================
# CONFIG
# =========================
TESSERACT_EXE = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE

INPUT_DIR = Path("input_screenshots")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


# =========================
# HELPERS
# =========================
def clean_text(s: str) -> str:
    s = s.upper()
    s = re.sub(r"[^A-Z0-9 +\-_/]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def run_ocr(bgr, psms=(6, 7, 11)) -> list[str]:
    """Return multiple OCR candidate strings (cleaned), one per PSM."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    out = []
    for psm in psms:
        txt = pytesseract.image_to_string(thr, config=f"--oem 3 --psm {psm}")
        txt = clean_text(txt)
        if txt:
            out.append(txt)
    return out


def ocr_title_area(img_bgr):
    """
    Crop the region where the 'Association ...' title appears.
    This crop is intentionally moderate to capture the title reliably.
    """
    h, w = img_bgr.shape[:2]
    y1, y2 = int(h * 0.02), int(h * 0.13)
    x1, x2 = int(w * 0.05), int(w * 0.82)
    return img_bgr[y1:y2, x1:x2]


def classify_title(text: str) -> str:
    """
    Fuzzy matching for titles + common abbreviations produced by OCR.
    """
    t = text

    # Full-ish matches
    if "ROSTER" in t and ("VIEWER" in t or "VIEW" in t):
        return "RosterViewer"
    if "TEAM" in t and "STAND" in t:
        return "TeamStandings"
    if "CONTRACT" in t and ("EXTEN" in t or "EXT" in t):
        return "ContractExtensions"
    if "FUTURE" in t and "DRAFT" in t:
        return "FutureDraftPicks"
    if "DRAFT" in t and "PICK" in t:
        return "FutureDraftPicks"

    # Abbreviations seen in your OCR
    if re.search(r"\bRV\b", t):
        return "RosterViewer"
    if re.search(r"\bTS\b", t) or re.search(r"\bTSI\b", t):
        return "TeamStandings"
    if re.search(r"\bCE\b", t):
        return "ContractExtensions"
    if re.search(r"\bFDP\b", t):
        return "FutureDraftPicks"

    return "Unknown"


def has_mynba_signal(text: str) -> bool:
    """
    Decide if this screenshot is likely a MyNBA screen based on title-area OCR.
    This is safer than trying to OCR logos.
    """
    signals = [
        "ASSOCIATION",
        "ROSTER", "VIEWER", "RV",
        "TEAM", "STAND", "TS", "TSI",
        "CONTRACT", "EXT", "CE",
        "FUTURE", "DRAFT", "PICK", "FDP",
        "MYNBA",
    ]
    return any(s in text for s in signals)


def pick_best_header(candidates: list[str]) -> str:
    """
    Choose the OCR candidate with the strongest MyNBA signals.
    """
    def score(t: str) -> float:
        sigs = ["ROSTER", "VIEWER", "TEAM", "STAND", "CONTRACT", "EXT", "FUTURE", "DRAFT", "PICK", "RV", "TSI", "CE", "FDP", "ASSOCIATION", "MYNBA"]
        return sum(1 for s in sigs if s in t) + len(t) * 0.001

    if not candidates:
        return ""
    return max(candidates, key=score)


# =========================
# MAIN
# =========================
def main():
    files = sorted([p for p in INPUT_DIR.glob("*") if p.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]])
    if not files:
        print(f"No images found in {INPUT_DIR.resolve()}")
        return

    manifest = []

    for p in files:
        img = cv2.imread(str(p))
        if img is None:
            manifest.append({"file": p.name, "screen_type": "Unreadable", "header_text": ""})
            print(f"{p.name:60s} -> Unreadable")
            continue

        title_crop = ocr_title_area(img)
        candidates = run_ocr(title_crop)
        header_text = pick_best_header(candidates)

        if not header_text or not has_mynba_signal(header_text):
            screen_type = "Ignore"
        else:
            screen_type = classify_title(header_text)

        manifest.append({"file": p.name, "screen_type": screen_type, "header_text": header_text})
        print(f"{p.name:60s} -> {screen_type:18s} | {header_text}")

    out_path = OUTPUT_DIR / "manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nSaved: {out_path.resolve()}")


if __name__ == "__main__":
    main()

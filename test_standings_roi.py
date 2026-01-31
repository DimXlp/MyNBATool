import cv2
import pytesseract
from pathlib import Path

# Load the standings screenshot
img = cv2.imread("input_screenshots/NBA 2K26 1_26_2026 9_41_40 PM.png")

# Test current ROIs
STANDINGS_RANK_COL_ROI = (88, 430, 30, 280)
STANDINGS_TEAM_COL_ROI = (210, 430, 200, 280)
STANDINGS_WL_COL_ROI = (390, 430, 80, 280)

def crop_roi(img, roi):
    x, y, w, h = roi
    return img[y:y+h, x:x+w]

rank_col = crop_roi(img, STANDINGS_RANK_COL_ROI)
team_col = crop_roi(img, STANDINGS_TEAM_COL_ROI)
wl_col = crop_roi(img, STANDINGS_WL_COL_ROI)

# Save debug images
Path("output/test_roi").mkdir(parents=True, exist_ok=True)
cv2.imwrite("output/test_roi/rank_col.png", rank_col)
cv2.imwrite("output/test_roi/team_col.png", team_col)
cv2.imwrite("output/test_roi/wl_col.png", wl_col)

print("Debug images saved to output/test_roi/")
print(f"Rank column shape: {rank_col.shape}")
print(f"Team column shape: {team_col.shape}")
print(f"W-L column shape: {wl_col.shape}")

# Try OCR on W-L column
wl_gray = cv2.cvtColor(wl_col, cv2.COLOR_BGR2GRAY)
wl_text = pytesseract.image_to_string(wl_gray, config="--psm 6")
print(f"\nW-L column OCR result:\n{wl_text}")

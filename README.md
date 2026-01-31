# NBA Roster Extraction Tool

An OCR-based tool for extracting player roster information from NBA game screenshots. This tool automatically identifies and extracts player names, positions, ages, overall ratings, and rating changes from RosterViewer screenshots.

## Features

- **Automated Player Detection**: Extracts player information from screenshots using OCR
- **Multi-Column Support**: Captures name, position (POS), age (AGE), overall rating (OVR), and rating changes (IN)
- **Smart Name Normalization**: Handles common OCR errors and formats names consistently (e.g., "J. Brunson", "C. Porter Jr.", "G. Hill II")
- **Rating Change Detection**: Detects upward (▲) and downward (▼) rating changes with deltas
- **Debug Mode**: Optional debug output with intermediate processing images
- **Configurable ROI**: Easily adjustable regions of interest for different screenshot layouts

## Prerequisites

### Required Software

1. **Python 3.7+**
2. **Tesseract OCR**
   - Windows: Download from [GitHub Tesseract Releases](https://github.com/UB-Mannheim/tesseract/wiki)
   - After installation, ensure `tesseract --version` works in your terminal
   - If not in PATH, set `TESSERACT_CMD` in `extract_roster_names.py`

### Python Dependencies

```bash
pip install -r requirements.txt
```

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/nba-roster-extraction-tool.git
cd nba-roster-extraction-tool
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install Tesseract OCR (see Prerequisites above)

4. Configure Tesseract path if needed:
   - Open `extract_roster_names.py`
   - Set `TESSERACT_CMD` to your tesseract.exe path if it's not in your PATH

## Project Structure

```
MyNBATool/
├── classify_screens.py          # Screen classification script
├── extract_roster_names.py      # Main roster extraction script
├── input_screenshots/           # Place your screenshots here
├── output/                      # Generated output files
│   ├── manifest.json           # Screenshot metadata
│   ├── roster_names.json       # List of unique player names
│   ├── roster_players.json     # Full player data with stats
│   ├── roster_names_raw.json   # Raw OCR results
│   └── debug_roster/           # Debug images (with --debug flag)
├── README.md
├── requirements.txt
└── .gitignore
```

## Usage

### Step 1: Classify Screenshots

First, classify your screenshots to identify RosterViewer screens:

```bash
python classify_screens.py
```

This generates `output/manifest.json` with metadata about each screenshot.

### Step 2: Extract Roster Data

Run the extraction script:

```bash
python extract_roster_names.py
```

For debug output with intermediate processing images:

```bash
python extract_roster_names.py --debug
```

### Output Files

- **roster_names.json**: Sorted list of unique player names
- **roster_players.json**: Complete player data including:
  - Name (normalized format)
  - Position (PG, SG, SF, PF, C)
  - Age
  - Overall rating (OVR)
  - Rating change delta (IN) with direction (+/-)
  - Source file and OCR confidence
- **roster_names_raw.json**: Raw OCR results for all detected text lines
- **debug_roster/**: (with --debug) Intermediate processing images

## Configuration

### Adjusting ROI (Region of Interest)

If your screenshots have different layouts, adjust these values in `extract_roster_names.py`:

```python
# ROI format: (x, y, width, height)
NAME_COL_ROI = (78, 495, 254, 469)    # NAME column
POS_COL_ROI = (340, 495, 70, 469)     # POS column
AGE_COL_ROI = (449, 495, 59, 469)     # AGE column
RATING_COL_ROI = (563, 495, 58, 469)  # RATING column
IN_COL_ROI = (620, 495, 50, 469)      # IN column (rating change)
```

### Finding ROI Coordinates

1. Run with `--debug` flag to generate debug images
2. Use an image viewer to measure pixel coordinates
3. Update the ROI values in the script
4. Test with a few screenshots to verify

## Examples

### Sample Output (roster_players.json)

```json
[
  {
    "name": "J. Brunson",
    "pos": "PG",
    "age": 28,
    "ovr": 85,
    "in_delta": 2,
    "in_str": "+2",
    "source": "screenshot_001.png",
    "name_conf": 92.5
  },
  {
    "name": "C. Porter Jr.",
    "pos": "SF",
    "age": 24,
    "ovr": 79,
    "in_delta": -1,
    "in_str": "-1",
    "source": "screenshot_002.png",
    "name_conf": 88.3
  }
]
```

## Troubleshooting

### "Tesseract is not installed or not reachable"

1. Verify Tesseract is installed: `tesseract --version`
2. If not in PATH, set `TESSERACT_CMD` in the script:
```python
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

### Poor OCR Results

- Use `--debug` flag to inspect intermediate images
- Adjust ROI coordinates if columns are misaligned
- Ensure screenshots are high quality and not compressed
- Check that the NAME column ROI only contains the yellow text column

### Missing or Incorrect Player Data

- POS/AGE/OVR columns use separate OCR strategies
- Verify ROI coordinates match your screenshot layout
- Check `debug_roster/` images to see what the OCR is processing
- Some fields may be None if OCR confidence is too low

## Technical Details

### OCR Strategy

- **Name Column**: Multiple PSM (Page Segmentation Mode) attempts with confidence scoring
- **Position**: Character whitelist for valid positions (PG/SG/SF/PF/C)
- **Age/Rating**: Digit-only whitelist with range validation
- **Rating Changes**: Color detection (green=up, red=down) + shape analysis for arrows

### Name Normalization

Automatically handles:
- Initial formatting: "J.Brunson" → "J. Brunson"
- Suffix normalization: "Jr" → "Jr.", "II" → "II"
- Roman numerals: uppercase and consistent formatting
- Common OCR errors: "l." → "I.", "Mi." → "M."

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Uses [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) for text recognition
- Built with [OpenCV](https://opencv.org/) and [pytesseract](https://github.com/madmaze/pytesseract)

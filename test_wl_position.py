import cv2

# Load standings screenshot
img = cv2.imread("input_screenshots/NBA 2K26 1_26_2026 9_41_40 PM.png")

# Draw a red rectangle on where I think the table is
# Looking at the screenshot: Row 2 (New York Knicks) appears around y=398-430
# W-L column appears around x=390-445

# Let me test different x positions for W-L
for x_start in range(380, 420, 5):
    test_roi = img[398:430, x_start:x_start+65].copy()
    cv2.imwrite(f"output/test_roi/wl_test_x{x_start}.png", test_roi)
    print(f"Saved W-L test at x={x_start}")

print("Check the images to see which one captures '20-11'")

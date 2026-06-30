# save as calibrate.py and run it
import pyautogui
import time

print("Move your mouse to each position. Coords print every second.")
print("Press Ctrl+C to stop.\n")
time.sleep(3)

try:
    while True:
        x, y = pyautogui.position()
        print(f"  x={x}, y={y}", end="\n")
        time.sleep(0.5)
except KeyboardInterrupt:
    print("\nDone")

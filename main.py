import mss 
from vision.capture import capture
# we gon pass this object to the capture function from vision/capture anytime screen capture is required
mss_instance = mss.MSS()


def main():
    capture_path = capture({"top": 0, "left": 0, "width": 800, "height": 800}, mss_instance)
    print(capture_path)
    print("Hello from clashautofarm!")


if __name__ == "__main__":
    main()

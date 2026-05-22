import mss 
import os
import time
from pathlib import Path

def capture(capture_region, mss_object):
    base_dir = str(Path(__file__).resolve().parent.parent)
    file_save_path = os.path.join(base_dir, 'mss_captures')
    os.makedirs(file_save_path, exist_ok=True)
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    microseconds = int((time.time() % 1) * 1000000)
    file_name = f'ss_{timestamp}_{microseconds:06d}.png'

    full_output_path = os.path.join(file_save_path, file_name)
    sct_img = mss_object.grab(capture_region)
    mss.tools.to_png(sct_img.rgb, sct_img.size, output=full_output_path)

    return full_output_path
        


    

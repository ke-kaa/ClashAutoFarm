import cv2 
from pathlib import Path

def load_template(template_dir="../assets/templates/"):
    templates = {}
    
    for path in Path(template_dir).glob("*.png"):
        templates[path.stem] = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)

    return templates

def find(screen, template_name, threshold=0.3):
    res = cv2.matchTemplate(cv2.imread(screen, cv2.IMREAD_GRAYSCALE), template_name, cv2.TM_CCOEFF_NORMED)
    
    _, max_val, _, _ = cv2.minMaxLoc(res)
    print(max_val)
    return max_val >= threshold

def is_disconnected(screen, templates):
    return find(screen, template_name=templates["wifi_disconnected"])

def  is_reconnect_popup(screen, templates):
    return find(screen, template_name=templates["reconnect_popup"])


def is_onscout_screen(screen, templates):
    return find(screen, templates["scout_screen"])


import mss
from vision import templates
import vision
from vision.capture import capture
from vision.ocr import extract_loot
#from vision.preprocess import to_gray_scale
import yaml
import cv2
# we gon pass this object to the capture function from vision/capture anytime screen capture is required
mss_instance = mss.MSS()
templates_dir = "/home/kaku/Documents/PersonalProjects/ClashAutoFarm/assets/templates/"

templates_dict = templates.load_template(templates_dir)

def main():
    #with open('./config.yaml', 'r') as file: 
     #   config = yaml.safe_load(file)

    #print(config)
    #loots = extract_loot("/home/kaku/Documents/PersonalProjects/ClashAutoFarm/vision/test_gray_scale.png")
    #capture_path = capture({"top": 0, "left": 0, "width": 800, "height": 800}, mss_instance)
    #print(type(loots))
    #print(loots)
    
    #output_path = to_gray_scale("/home/kaku/Documents/PersonalProjects/ClashAutoFarm/testImage.png")
    #print(output_path)
    # process image using teserract to extract loot 
    print("Hello from clashautofarm!")
    print(templates_dict)
    print("Test wifi disconnected screen")
    d1 = templates.is_disconnected("./assets/templates/Screenshot 2026-05-22 124033.png", templates_dict)
    print(f"True: {d1}")
    d2 = templates.is_disconnected("./assets/templates/Screenshot 2026-05-22 124138.png", templates_dict)
    print(f"True: {d2}")
    d3 = templates.is_disconnected("./assets/templates/Screenshot 2026-05-22 124150.png", templates_dict)
    print(f"True: {d3}")
    d4 = templates.is_disconnected("./assets/templates/Screenshot 2026-05-22 124349.png", templates_dict)
    print(f"False: {d4}")
    d5 = templates.is_disconnected("./assets/templates/Screenshot 2026-05-22 124625.png", templates_dict)
    print(f"False: {d5}")
    d6 = templates.is_disconnected("./assets/templates/Screenshot 2026-05-22 124650.png", templates_dict)
    print(f"False: {d6}")
    print(f"True: {templates.is_disconnected("./assets/templates/wifi_disconnected.png", templates_dict)}")
    print()
    print()
    print("Test finding base screen") 
    d7 = templates.is_onscout_screen("./assets/templates/Screenshot 2026-05-22 124033.png", templates_dict)
    print(f"True: {d7}")
    d8 = templates.is_onscout_screen("./assets/templates/Screenshot 2026-05-22 124238.png", templates_dict)
    print(f"False: {d8}")
    print()
    print()
    d9 = templates.is_reconnect_popup("./assets/templates/Screenshot 2026-05-22 124349.png", templates_dict)
    print(f"True: {d9}")
    d10 = templates.is_reconnect_popup("./assets/templates/Screenshot 2026-05-22 124625.png", templates_dict)
    print(f"False: {d10}")
    d11 = templates.is_reconnect_popup("./assets/templates/Screenshot 2026-05-22 124642.png", templates_dict)
    print(f"False: {d11}")
    #p = "/home/kaku/Documents/PersonalProjects/ClashAutoFarm/assets/templates/Screenshot 2026-05-22 124150.png"
    #image = cv2.imread(p, 0)
    #cv2.imshow('image', image)
    #cv2.waitKey(0)
    #cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

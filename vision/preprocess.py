import cv2
import os
import time
from pathlib import Path
import yaml

with open("../config.yaml", "r") as file:
    config = yaml.safe_load(file)

def to_gray_scale(image_path):
    image_path = Path(image_path)

    img = cv2.imread(str(image_path))

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    output_path = image_path.parent / f"gray_{image_path.name}"

    cv2.imwrite(str(output_path), gray)

    return output_path

def check_threshold_for_townhall(townhall_level, loots):
    if loots["dark_elixir"] >= config["threshold"][townhall_level]:
        return True
    
    return loots["gold"] + loots["elixir"] >= config["threshold"][townhall_level]["gold_elixir_total"]

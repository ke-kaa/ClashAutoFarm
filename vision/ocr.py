import pytesseract 

def extract_loot(image_path):
    loot = pytesseract.image_to_string(image_path)
    loots = loot.split('\n')

    return { "gold": loots[0], "elixir": loots[1], "dark_elixir": loots[2]}

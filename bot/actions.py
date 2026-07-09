"""
bot/actions.py — Click/drag wrappers for Clash of Clans automation.
"""

import pyautogui
import random
import time


pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5



def _jitter(value, amount=5):
    """Add small random offset to a coordinate."""
    return value + random.randint(-amount, amount)


def _random_delay(low=0.05, high=0.15):
    """Sleep a tiny random duration between actions."""
    time.sleep(random.uniform(low, high))



def click(x, y, jitter=True):
    """Click a screen position with optional jitter."""
    if jitter:
        x, y = _jitter(x), _jitter(y)
    pyautogui.click(x, y)


def drag(start_x, start_y, end_x, end_y, duration=1.0):
    """Click-and-drag from one point to another."""
    pyautogui.moveTo(start_x, start_y)
    pyautogui.mouseDown(button='left')
    pyautogui.moveTo(end_x, end_y, duration=duration)
    pyautogui.mouseUp(button='left')


def scroll(amount):
    """Scroll the mouse wheel."""
    pyautogui.scroll(amount)


def wait(seconds):
    """Sleep for a given number of seconds."""
    time.sleep(seconds)



def click_attack_button(x=142, y=880, times=3):
    """Tap the Attack button on the home screen."""
    for _ in range(times):
        click(x, y)
        _random_delay()


def click_find_match(x=259, y=724):
    """Tap 'Find a Match' after the attack menu is open."""
    click(x, y)


def click_confirm_attack(x=1284, y=846):
    """Confirm the attack when prompted."""
    click(x, y)


def wait_for_match(seconds=8):
    """Wait for matchmaking to finish."""
    wait(seconds)


def click_next(x=1400, y=777):
    """Skip the current base during scouting."""
    click(x, y)


def click_reconnect(x=700, y=450):
    """Dismiss the reconnect popup."""
    click(x, y)



def zoom_in(amount=-10000):
    """Zoom the camera all the way in."""
    scroll(amount)


def adjust_camera(start, end, duration=1.0):
    """Drag the camera to reposition the view."""
    drag(start[0], start[1], end[0], end[1], duration=duration)



def select_troop(x, y):
    """Select a troop from the bottom bar by clicking its slot."""
    click(x, y)


def deploy_troop_drag(troop_slot, drag_start, drag_end, duration=1.5):
    """Select a troop slot then deploy via drag."""
    select_troop(*troop_slot)
    _random_delay()
    drag(drag_start[0], drag_start[1], drag_end[0], drag_end[1], duration=duration)


def deploy_troop_click(troop_slot, target):
    """Select a troop slot then deploy with a single click."""
    select_troop(*troop_slot)
    _random_delay()
    click(target[0], target[1])


def deploy_spell(spell_slot, target, count=1):
    """Select a spell slot then tap the target `count` times."""
    select_troop(*spell_slot)
    _random_delay()
    for _ in range(count):
        click(target[0], target[1])
        _random_delay(0.05, 0.1)


def activate_hero_ability(hero_slot):
    """Activate a hero's ability by clicking its slot."""
    click(hero_slot[0], hero_slot[1])


def activate_all_hero_abilities(hero_slots):
    """Activate abilities for all heroes in order."""
    for slot in hero_slots:
        activate_hero_ability(slot)
        _random_delay()


def end_battle(button_pos=(140, 794), confirm_pos=(918, 658)):
    """Tap the end-battle button, then confirm."""
    click(button_pos[0], button_pos[1])
    _random_delay()
    click(confirm_pos[0], confirm_pos[1])


def return_home(button_pos=(784, 853), taps=2):
    """Tap the 'Return Home' button."""
    for _ in range(taps):
        click(button_pos[0], button_pos[1])
        _random_delay()


def wait_for_result_screen(seconds=14):
    """Wait for the post-battle result/loot screen to clear."""
    wait(seconds)


def claim_treasure_reward(cfg):
    """
    Treasure hunt claim sequence.
    cfg=config['treasure_hunt']
    Tap Claim Reward -> N advanced taps through reward screen -> wait -> 1 final tap.
    """
    click(*cfg["claim_button"])
    _random_delay()
    for pos in cfg["advanced_clicks"]:
        click(*pos)
        _random_delay()
    wait(cfg["final_click_delay"])
    click(*cfg["final_click"])

    

def auto_farm():
    """Execute a complete attack cycle."""
    click_attack_button()
    click_find_match()
    click_confirm_attack()
    wait_for_match(seconds=8)

    zoom_in()
    adjust_camera(start=(770, 409), end=(1081, 829))

    deploy_troop_drag(
        troop_slot=(304, 906),
        drag_start=(847, 198),
        drag_end=(268, 653),
        duration=1.5,
    )

    deploy_troop_click(troop_slot=(404, 905), target=(572, 420))

    hero_slots = [
        (513, 900),
        (598, 900),
        (694, 906),
        (787, 906),
    ]
    for slot in hero_slots:
        deploy_troop_click(troop_slot=slot, target=(572, 420))

    wait(10)

    deploy_spell(spell_slot=(860, 906), target=(572, 420), count=11)

    wait(10)
    activate_hero_ability((404, 900))
    activate_all_hero_abilities(hero_slots)

    wait(35)

    end_battle()
    return_home()
    wait_for_result_screen(seconds=14)

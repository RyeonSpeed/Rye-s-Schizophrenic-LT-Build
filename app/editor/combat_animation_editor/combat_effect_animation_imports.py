import os

from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QPixmap

from app.data.resources.resources import RESOURCES
from app.data.resources import combat_anims, combat_commands
from app.editor.combat_animation_editor.combat_animation_imports import convert_gba, split_doubles, combine_identical_commands
from app.editor.combat_animation_editor.combat_effect_sound_table import SOUND_TABLE


import logging

# Imports Spell Animations

# Object Frames:
# Object Frames are 480 x 160 pixels, the first 240x160 is the foreground in front of the battle animations
# the second 240x160 is drawn behind the battle animations

# Background Frames:
# 240x160 px, drawn in front of battle animations, but below object frame foreground

# Top right of Background frame image is background color, defaults to (0, 0, 0)

# Originally prototyped by MKCocoon and DecklynKern

BG_WIDTH, BG_HEIGHT = 480, 160

def parse_spell_txt(fn, pixmaps):
    with open(fn) as fp:
        script_lines = [line.strip() for line in fp.readlines()]
        # Remove comment lines
        script_lines = [(line[:line.index('#')] if '#' in line else line) for line in script_lines]
        script_lines = [line for line in script_lines if line]  # Remove empty lines

    stretch_foreground = False
    miss_terminator_reached = False

    last_global_counter = 0  # Keeps track of what frame the last command to the main controller effect was added to
    current_counter = 0  # Keeps track of what frame the main controller effect should be on

    # This creates six lists of commands
    global_hit_commands = []
    global_miss_commands = []
    # For the object frames of the hit/attack pose
    hit_effect_commands = []
    # For the background frames of the hit/attack pose
    hit_under_effect_commands = []
    # For the object frames of the miss pose
    miss_effect_commands = []
    # For the background frames of the miss pose
    miss_under_effect_commands = []

    def parse_text(command_text: str, hit_only: bool = False, miss_only: bool = False):
        command = combat_commands.parse_text(command_text)
        # Add necessary waits to match up with the child effects
        if current_counter > last_global_counter:
            wait_command = combat_commands.parse_text(f'wait;{current_counter - last_global_counter}')
            global_hit_commands.append(wait_command)
            global_miss_commands.append(wait_command)

        if not miss_only:
            global_hit_commands.append(command)
        if not hit_only:
            global_miss_commands.append(command)
        nonlocal last_global_counter
        last_global_counter = current_counter

    def process_command(line: str):
        arg1 = int(line[1:3], 16)
        arg2 = int(line[3:5], 16)
        command_code = line[5:]

        # 00 through 13 (except 08) are ignored
        if command_code == '08':
            pass  # Attack (becomes critical automatically) with HP stealing
        # 14 through 28: passed to attacker's animation
        elif command_code == '14':
            parse_text('screen_shake')
        elif command_code == '15':
            parse_text('platform_shake')
        elif command_code == '1A':  # Start hit
            parse_text('enemy_flash_white;8', hit_only=True)
            parse_text('wait;1')
            nonlocal last_global_counter
            last_global_counter += 1  # Account for wait
            parse_text('screen_flash_white;4', hit_only=True)
        elif command_code in ('1F', '20', '21'):  # spell hit or spell miss
            parse_text('spell_hit', hit_only=True)
            parse_text('miss', miss_only=True)
        elif command_code == '29':  # Set brightness and opacity levels
            dimness = int(arg1 / 0x10 * 255)  # multiply by 255 to get into LT format
            opacity = int(1.0 - (arg2 / 0x10 / 2) * 255)
            parse_text(f'set_dimness;{dimness}')
            parse_text(f'opacity;{opacity}')
        elif command_code == '2A':  # Whether maps 2 and 3 of the GBA screen should be visible
            # display_maps = (arg2 != 0)
            pass
        # 2B through 3F: passed to attacker's animation
        elif command_code == '40':  # Scrolls screen from being centered on the attacker to being centered on the defender
            parse_text("pan")
        # 41 through 47: passed to attacker's animation
        elif command_code == '48':  # Plays sound or music whose ID corresponds to those documented in Music List.txt of the nightmare module packages
            sound_id = arg1 * 256 + arg2
            sound_name = SOUND_TABLE[sound_id]
            parse_text(f"sound;{sound_name}")
        # 49 through 51: passed to attacker's animation
        elif command_code == '53':  # Enable screen stretch
            stretch_foreground = bool(arg2)

    for idx, line in enumerate(script_lines):
        logging.info(f"Processing script line: {line}")

        if line.startswith('/// - '):
            pass

        elif line.startswith('C'):
            process_command(line)

        elif line.startswith('O'):
            object_image_fn = line.split()[-1]
            object_image_name = object_image_fn[:-4]  # Remove .png
            background_image_fn = script_lines[idx + 1].split()[-1]
            background_image_name = background_image_fn[:-4] # Remove .png
            num_frames = int(script_lines[idx + 2])

            if object_image_name not in pixmaps:
                logging.error(f"{object_image_name} not in pixmaps")
            object_frame_command = combat_commands.parse_text(f'f;{num_frames};{object_image_name}')

            if background_image_name not in pixmaps:
                logging.error(f"{background_image_name} not in pixmaps")
            under_background_image_name = background_image_name + '_under'
            if under_background_image_name not in pixmaps:
                logging.error(f"{under_background_image_name} not in pixmaps")
            background_frame_command = combat_commands.parse_text(f'f;{num_frames};{background_image_name};{under_background_image_name}')

            hit_effect_commands.append(object_frame_command)
            miss_effect_commands.append(object_frame_command)

            hit_under_effect_commands.append(background_frame_command)
            miss_under_effect_commands.append(background_frame_command)

            current_counter += num_frames

        elif line.startswith('~'):  # Miss terminator
            miss_terminator_reached = True

    # At the end of the parse, break out of the spell
    parse_text('end_parent_loop')
    parse_text('wait;1')

    return global_hit_commands, global_miss_commands, \
        hit_effect_commands, miss_effect_commands, \
        hit_under_effect_commands, miss_under_effect_commands

def import_effect_from_gba(fn: str, effect_name: str):
    """
    Imports spell animations from a properly formatted GBA CSA script file
    and creates a new spell effect animation

    Parameters
    ----------
    fn: str, filename
        "*.txt" file to read from
    effect_name: str
        What the nid of the new effect should be
    """
    directory = os.path.split(os.path.abspath(fn))[0] 
    logging.info(f"Import GBA weapon animation from script {fn} in {directory}")

    foreground_effect_name = effect_name + '_fg'
    background_effect_name = effect_name + '_bg'

    images = []
    for image_fn in os.listdir(directory):
        if image_fn.endswith('.png'):
            images.append(os.path.join(directory, image_fn))
    logging.info("Images located: %s", images)
    if not images:
        QMessageBox.critical(None, "Error", "Cannot find valid images in %s!" % directory)
        return

    # Convert to pixmaps
    pixmaps = {os.path.split(path)[-1][:-4]: QPixmap(path) for path in images}
    # Convert to GBA colors
    pixmaps = {name: convert_gba(pix) for name, pix in pixmaps.items()}
    # Split double images into "_under" image
    pixmaps = split_doubles(pixmaps)

    global_hit, global_miss, hit_effect, miss_effect, hit_under_effect, miss_under_effect = \
        parse_spell_txt(fn, pixmaps)

    # Place the child effects in the effect animation
    global_hit.insert(0, combat_commands.parse_text(f"effect;{foreground_effect_name}"))
    global_hit.insert(1, combat_commands.parse_text(f"under_effect;{background_effect_name}"))
    global_miss.insert(0, combat_commands.parse_text(f"effect;{foreground_effect_name}"))
    global_miss.insert(1, combat_commands.parse_text(f"under_effect;{background_effect_name}"))

    # Posify
    # Global Controller
    hit_pose = combat_anims.Pose("Attack")
    for command in global_hit:
        hit_pose.timeline.append(command.__class__.copy(command))
    miss_pose = combat_anims.Pose("Miss")
    for command in global_miss:
        miss_pose.timeline.append(command.__class__.copy(command))

    controller_effect = combat_anims.EffectAnimation(effect_name)
    controller_effect.poses.append(hit_pose)
    controller_effect.poses.append(miss_pose)

    # Regular Effect
    hit_pose = combat_anims.Pose("Attack")
    for command in hit_effect:
        hit_pose.timeline.append(command.__class__.copy(command))
    combine_identical_commands(hit_pose)
    miss_pose = combat_anims.Pose("Miss")
    for command in miss_effect:
        miss_pose.timeline.append(command.__class__.copy(command))
    combine_identical_commands(miss_pose)

    regular_effect = combat_anims.EffectAnimation(foreground_effect_name)
    regular_effect.poses.append(hit_pose)
    regular_effect.poses.append(miss_pose)

    # Under Effect
    hit_pose = combat_anims.Pose("Attack")
    for command in hit_under_effect:
        hit_pose.timeline.append(command.__class__.copy(command))
    combine_identical_commands(hit_pose)
    miss_pose = combat_anims.Pose("Miss")
    for command in miss_under_effect:
        miss_pose.timeline.append(command.__class__.copy(command))
    combine_identical_commands(miss_pose)

    under_effect = combat_anims.EffectAnimation(background_effect_name)
    under_effect.poses.append(hit_pose)
    under_effect.poses.append(miss_pose)

    RESOURCES.effect_anims.append(controller_effect)
    RESOURCES.effect_anims.append(regular_effect)
    RESOURCES.effect_anims.append(under_effect)

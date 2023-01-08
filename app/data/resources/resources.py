import shutil
import os
import traceback

from app import sprites
from app.utilities import exceptions
from app.data.resources.fonts import FontCatalog
from app.data.resources.icons import Icon16Catalog, Icon32Catalog, Icon80Catalog
from app.data.resources.portraits import PortraitCatalog
from app.data.resources.animations import AnimationCatalog
from app.data.resources.panoramas import PanoramaCatalog
from app.data.resources.map_icons import MapIconCatalog
from app.data.resources.map_sprites import MapSpriteCatalog
from app.data.resources.tiles import TileSetCatalog, TileMapCatalog
from app.data.resources.sounds import SFXCatalog, MusicCatalog
from app.data.resources.combat_palettes import PaletteCatalog
from app.data.resources.combat_anims import CombatCatalog, CombatEffectCatalog

import logging

class Resources():
    save_data_types = ("icons16", "icons32", "icons80", "portraits", "animations", "panoramas",
                       "map_icons", "map_sprites", "combat_palettes", "combat_anims", "combat_effects", "music", "sfx",
                       "tilesets", "tilemaps")
    loose_file_types = ["custom_components", "custom_sprites"]

    def __init__(self):
        self.main_folder = None

        # Modifiable Resources
        self.clear()

        # Standardized, Locked resources
        self.load_standard_resources()

        # custom components
        self.loaded_custom_components_path = None

    def load_standard_resources(self):
        self.platforms = self.get_sprites('resources', 'platforms')
        self.fonts = FontCatalog()
        self.fonts.load('resources/fonts')

    def get_sprites(self, home, sub):
        s = {}
        loc = os.path.join(home, sub)
        for root, dirs, files in os.walk(loc):
            for name in files:
                if name.endswith('.png'):
                    full_name = os.path.join(root, name)
                    s[name[:-4]] = full_name
        return s

    def get_platform_types(self):
        names = list(sorted({fn.split('-')[0] for fn in self.platforms.keys()}))
        sprites = [n + '-Melee' for n in names]
        return list(zip(names, sprites))

    def clear(self):
        self.icons16 = Icon16Catalog()
        self.icons32 = Icon32Catalog()
        self.icons80 = Icon80Catalog()

        self.portraits = PortraitCatalog()
        self.animations = AnimationCatalog()

        self.panoramas = PanoramaCatalog()
        self.map_icons = MapIconCatalog()
        self.map_sprites = MapSpriteCatalog()
        self.combat_palettes = PaletteCatalog()
        self.combat_anims = CombatCatalog()
        self.combat_effects = CombatEffectCatalog()

        self.tilesets = TileSetCatalog()
        self.tilemaps = TileMapCatalog()

        self.music = MusicCatalog()
        self.sfx = SFXCatalog()

    def load(self, proj_dir, specific=None):
        self.main_folder = os.path.join(proj_dir, 'resources')

        # Load custom sprites for the UI
        # This should overwrite the regular sprites in the "/sprites" folder
        sprites.reset()
        sprites.load_sprites(os.path.join(self.main_folder, 'custom_sprites'))

        if specific:
            save_data_types = specific
        else:
            save_data_types = self.save_data_types
        for data_type in save_data_types:
            print("Loading %s from %s..." % (data_type, self.main_folder))
            logging.info("Loading %s from %s..." % (data_type, self.main_folder))
            getattr(self, data_type).clear()  # Now always clears first
            getattr(self, data_type).load(os.path.join(self.main_folder, data_type))

        # load custom components
        self.load_components()

    def load_components(self):
        # For getting custom project components at runtime
        import importlib
        import importlib.util
        import os
        import sys

        cc_path = self.get_custom_components_path()

        if not cc_path:
            self.loaded_custom_components_path = None
            return

        module_path = os.path.join(cc_path, '__init__.py')
        if module_path != self.loaded_custom_components_path and os.path.exists(module_path):
            self.loaded_custom_components_path = module_path
            print("Importing Custom Components")
            try:
                spec = importlib.util.spec_from_file_location('custom_components', module_path)
                module = importlib.util.module_from_spec(spec)
                # spec.name is 'custom_components'
                sys.modules[spec.name] = module
                spec.loader.exec_module(module)
            except:
                import_failure_msg = traceback.format_exc()
                logging.error("Failed to import custom components: %s" % (import_failure_msg))
                raise exceptions.CustomComponentsException("Failed to import custom components: %s" % (import_failure_msg))
        if not os.path.exists(module_path):
            self.loaded_custom_components_path = None

    def save(self, proj_dir, specific=None, progress=None):
        logging.warning("Starting Resource Serialization...")
        import time
        start = time.time_ns()/1e6
        # Make the directory to save this resource pack in
        if not os.path.exists(proj_dir):
            os.mkdir(proj_dir)
        resource_dir = os.path.join(proj_dir, 'resources')
        if not os.path.exists(resource_dir):
            os.mkdir(resource_dir)

        should_save_loose_files = False
        if specific:
            save_data_types = specific
        else:
            save_data_types = self.save_data_types
            should_save_loose_files = True
        for idx, data_type in enumerate(save_data_types):
            data_dir = os.path.join(resource_dir, data_type)
            if not os.path.exists(data_dir):
                os.mkdir(data_dir)
            logging.warning("Saving %s..." % data_type)
            time1 = time.time_ns()/1e6
            getattr(self, data_type).save(data_dir)
            time2 = time.time_ns()/1e6 - time1
            logging.warning("Time Taken: %s ms" % time2)
            if progress:
                progress.setValue(int(idx / len(save_data_types) * 75))
        if should_save_loose_files and self.main_folder:
            for loose_file_type in self.loose_file_types:
                logging.warning("Saving %s..." % loose_file_type)
                time1 = time.time_ns()/1e6
                target_dir = os.path.join(resource_dir, loose_file_type)
                if not os.path.exists(target_dir) and os.path.exists(os.path.join(self.main_folder, loose_file_type)):
                    shutil.copytree(os.path.join(self.main_folder, loose_file_type), target_dir)
                time2 = time.time_ns()/1e6 - time1
                logging.warning("Time Taken: %s ms" % time2)
                if progress:
                    progress.setValue(80)


        end = time.time_ns()/1e6
        logging.warning("Total Time Taken for Resources: %s ms" % (end - start))
        logging.warning('Done Resource Serializing!')

    def clean(self, proj_dir) -> bool:
        """
        Returns bool -> whether cleaning was successful
        """
        logging.warning("Starting Resource Cleaning...")
        import time
        start = time.time_ns()/1e6

        if not os.path.exists(proj_dir):
            return False
        resource_dir = os.path.join(proj_dir, 'resources')
        if not os.path.exists(resource_dir):
            return False

        for idx, data_type in enumerate(self.save_data_types):
            data_dir = os.path.join(resource_dir, data_type)
            if not os.path.exists(data_dir):
                continue
            try:
                getattr(self, data_type).clean(data_dir)
            except Exception as e:
                logging.exception(e)
                logging.error("Could not successfully clean %s" % data_type)

        end = time.time_ns() / 1e6
        logging.warning("Total Time Taken for cleaning resource directory: %s ms" % (end - start))
        logging.warning("Done Resource Cleaning!")
        return True

    def has_loaded_custom_components(self):
        return self.loaded_custom_components_path

    def get_custom_components_path(self):
        if self.main_folder:
            return os.path.join(self.main_folder, 'custom_components')
        return None


RESOURCES = Resources()

# Testing
# Run "python -m app.data.resources.resources" from main directory

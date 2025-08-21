from app.engine.sound import get_sound_thread

class UnitSound():
    sound_catalog = {
        'Flier': {0: 'Flier', 20: 'repeat'},
        'Mounted': {0: 'Mounted1', 3: 'Mounted2', 10: 'Mounted3', 21: 'repeat'},
        'Armor': {0: 'Armor1', 16: 'Armor2', 32: 'repeat'},
        'Infantry': {0: 'Infantry1', 8: 'Infantry2', 16: 'repeat'},
        'Mogall': {0: 'Mogall', 22: 'repeat'},
        'Spider': {0: 'Bael', 11: 'repeat'},
        'Skeleton': {0: 'Skeleton', 10: 'repeat'},
        'Zombie': {0: 'Zombie', 12: 'repeat'}}

    def __init__(self, unit):
        self.unit = unit
        self.frame = 0
        self.current_sound = 0
        self.playing_sound = 0

    def play(self):
        if self.unit.klass in ['Spider', 'Spider_Queen', 'Baellista']:
            self.current_sound = 'Spider'
        elif self.unit.klass in ['Bigle', 'Bigler', 'Tsukumogami_M', 'Tsukumogami_S']:
            self.current_sound = 'Mogall'
        elif self.unit.klass in ['Skeleton', 'Boneguard', 'Wight_King', 'Skeleton_B', 'Boneguard_B']:
            self.current_sound = 'Skeleton'
        elif self.unit.klass in ['Revenant', 'Entombed', 'Mermaid']:
            self.current_sound = 'Zombie'
        elif 'Flying' in self.unit.tags:
            self.current_sound = 'Flier'
        elif 'Mounted' in self.unit.tags:
            self.current_sound = 'Mounted'
        elif 'Armor' in self.unit.tags:
            self.current_sound = 'Armor'
        else:
            self.current_sound = 'Infantry'

    def update(self, volume=1):
        if self.current_sound:
            if self.frame in self.sound_catalog[self.current_sound]:
                sound = self.sound_catalog[self.current_sound][self.frame]
                if sound == 'repeat':
                    self.frame = -1
                else:
                    self.playing_sound = 'Map_Step_' + sound
                    get_sound_thread().play_sfx(self.playing_sound, volume=volume)
            self.frame += 1

    def stop(self):
        get_sound_thread().stop_sfx(self.playing_sound)
        self.current_sound, self.playing_sound = None, None
        self.frame = 0

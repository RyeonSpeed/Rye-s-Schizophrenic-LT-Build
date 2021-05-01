from app.utilities.data import Prefab

class EventCommand(Prefab):
    nid: str = None
    nickname: str = None
    tag: str = 'general'

    keywords: list = []
    optional_keywords: list = []
    flags: list = []

    values: list = []

    def __init__(self, values=None):
        self.values = values or []

    def save(self):
        return self.nid, self.values

    def to_plain_text(self):
        return ';'.join([self.nid] + self.values)

    def __repr__(self):
        return self.to_plain_text()

class Comment(EventCommand):
    nid = "comment"
    nickname = '#'
    tag = None

    def to_plain_text(self):
        return self.values[0]

class If(EventCommand):
    nid = "if"
    tag = "flow"

    keywords = ['Condition']

class Elif(EventCommand):
    nid = "elif"
    tag = "flow"

    keywords = ['Condition']

class Else(EventCommand):
    nid = "else"
    tag = "flow"

class End(EventCommand):
    nid = "end"
    tag = "flow"

class Break(EventCommand):
    nid = "break"
    tag = "flow"

class Wait(EventCommand):
    nid = "wait"
    tag = "general"

    keywords = ['Time']

class EndSkip(EventCommand):
    nid = "end_skip"
    tag = "general"

class Music(EventCommand):
    nid = "music"
    nickname = "m"
    tag = "sound"

    keywords = ['Music']
    optional_keywords = ['Time']  # How long to fade in (default 400)

class MusicClear(EventCommand):
    nid = "music_clear"
    nickname = "m"
    tag = "sound"

    optional_keywords = ['Time']  # How long to fade out

class Sound(EventCommand):
    nid = "sound"
    tag = "sound"

    keywords = ['Sound']

class ChangeMusic(EventCommand):
    nid = 'change_music'
    tag = 'sound'

    keywords = ['PhaseMusic', 'Music']

class AddPortrait(EventCommand):
    nid = "add_portrait"
    nickname = "u"
    tag = "dialogue"

    keywords = ['Portrait', 'ScreenPosition']
    optional_keywords = ['Slide', 'ExpressionList']
    flags = ["mirror", "low_priority", "immediate", "no_block"]

class MultiAddPortrait(EventCommand):
    nid = "multi_add_portrait"
    nickname = "uu"
    tag = "dialogue"

    keywords = ['Portrait', 'ScreenPosition', 'Portrait', 'ScreenPosition']
    optional_keywords = ['Portrait', 'ScreenPosition', 'Portrait', 'ScreenPosition']

class RemovePortrait(EventCommand):
    nid = "remove_portrait"
    nickname = "r"
    tag = "dialogue"

    keywords = ['Portrait']
    flags = ["immediate", "no_block"]

class MultiRemovePortrait(EventCommand):
    nid = "multi_remove_portrait"
    nickname = "rr"
    tag = "dialogue"

    keywords = ['Portrait', 'Portrait']
    optional_keywords = ['Portrait', 'Portrait']

class MovePortrait(EventCommand):
    nid = "move_portrait"
    tag = "dialogue"

    keywords = ['Portrait', 'ScreenPosition']
    flags = ["immediate", "no_block"]

class BopPortrait(EventCommand):
    nid = "bop_portrait"
    nickname = "bop"
    tag = "dialogue"

    keywords = ['Portrait']
    flags = ["no_block"]

class Expression(EventCommand):
    nid = "expression"
    nickname = "e"
    tag = "dialogue"

    keywords = ['Portrait', 'ExpressionList']

class Speak(EventCommand):
    nid = "speak"
    nickname = "s"
    tag = "dialogue"

    keywords = ['Speaker', 'Text']
    optional_keywords = ['ScreenPosition', 'Width', 'DialogVariant']
    flags = ['low_priority']

class Transition(EventCommand):
    nid = "transition"
    nickname = "t"
    tag = "background"

    optional_keywords = ['Direction', 'Speed', 'Color3']

class Background(EventCommand):
    # Also does remove background
    nid = "change_background"
    nickname = "b"
    tag = "background"

    optional_keywords = ['Panorama']
    flags = ["keep_portraits"]

class DispCursor(EventCommand):
    nid = "disp_cursor"
    tag = "cursor"
    keywords = ["Bool"]

class MoveCursor(EventCommand):
    nid = "move_cursor"
    nickname = "set_cursor"
    tag = "cursor"
    
    keywords = ["Position"]
    flags = ["immediate"]

class CenterCursor(EventCommand):
    nid = "center_cursor"
    tag = "cursor"
    
    keywords = ["Position"]
    flags = ["immediate"]

class FlickerCursor(EventCommand):
    nid = 'flicker_cursor'
    nickname = 'highlight'
    tag = 'cursor'

    keywords = ["Position"]
    flags = ["immediate"]

class GameVar(EventCommand):
    nid = 'game_var'
    tag = 'general'

    keywords = ["Nid", "Condition"]

class IncGameVar(EventCommand):
    nid = 'inc_game_var'
    tag = 'general'

    keywords = ["Nid"]
    optional_keywords = ["Condition"]

class LevelVar(EventCommand):
    nid = 'level_var'
    tag = 'general'

    keywords = ["Nid", "Condition"]

class IncLevelVar(EventCommand):
    nid = 'inc_level_var'
    tag = 'general'

    keywords = ["Nid"]
    optional_keywords = ["Condition"]

class WinGame(EventCommand):
    nid = 'win_game'
    tag = "general"

class LoseGame(EventCommand):
    nid = 'lose_game'
    tag = "general"

class ActivateTurnwheel(EventCommand):
    nid = 'activate_turnwheel'
    tag = 'general'

    # Whether to force the player to move the turnwheel back
    # defaults to true
    optional_keywords = ['Bool']  

class BattleSave(EventCommand):
    nid = 'battle_save'
    tag = 'general'

class ChangeTilemap(EventCommand):
    nid = 'change_tilemap'
    tag = 'general'

    keywords = ["Tilemap"]
    flags = ["reload"]  # Should place units in previously recorded positions

class LoadUnit(EventCommand):
    nid = 'load_unit'
    tag = 'unit'

    keywords = ["UniqueUnit"]
    optional_keywords = ["Team", "AI"]

class MakeGeneric(EventCommand):
    nid = 'make_generic'
    tag = 'unit'

    # Nid, class, level, team, ai, faction, anim variant
    keywords = ["String", "Klass", "String", "Team"]
    optional_keywords = ["AI", "Faction", "String", "ItemList"]

class CreateUnit(EventCommand):
    nid = 'create_unit'
    tag = 'unit'
    # Unit template and new unit nid (can be '')
    keywords = ["Unit", "String"]
    # Unit level, position, entrytype, placement
    optional_keywords = ["String", "Position", "EntryType", "Placement"]

class AddUnit(EventCommand):
    nid = 'add_unit'
    nickname = 'add'
    tag = 'unit'

    keywords = ["Unit"]
    optional_keywords = ["Position", "EntryType", "Placement"]

class MoveUnit(EventCommand):
    nid = 'move_unit'
    nickname = 'move'
    tag = 'unit'

    keywords = ["Unit"]
    optional_keywords = ["Position", "MovementType", "Placement"]
    flags = ['no_block', 'no_follow']

class RemoveUnit(EventCommand):
    nid = 'remove_unit'
    nickname = 'remove'
    tag = 'unit'

    keywords = ["Unit"]
    optional_keywords = ["RemoveType"]

class RemoveAllUnits(EventCommand):
    nid = 'remove_all_units'
    tag = 'unit'

class RemoveAllEnemies(EventCommand):
    nid = 'remove_all_enemies'
    tag = 'unit'

class InteractUnit(EventCommand):
    nid = 'interact_unit'
    nickname = 'interact'
    tag = 'unit'

    keywords = ["Unit", "Unit"]
    optional_keywords = ["CombatScript", "Ability"]

class SetCurrentHP(EventCommand):
    nid = 'set_current_hp'
    tag = 'unit'
    keywords = ["Unit", "PositiveInteger"]

class Resurrect(EventCommand):
    nid = 'resurrect'
    tag = 'unit'
    keywords = ["GlobalUnit"]

class Reset(EventCommand):
    nid = 'reset'
    tag = 'unit'
    keywords = ["Unit"]

class HasAttacked(EventCommand):
    nid = 'has_attacked'
    tag = 'unit'
    keywords = ["Unit"]

class HasTraded(EventCommand):
    nid = 'has_traded'
    tag = 'unit'
    keywords = ['Unit']

class AddGroup(EventCommand):
    nid = 'add_group'
    tag = 'unit'

    keywords = ["Group"]
    optional_keywords = ["StartingGroup", "EntryType", "Placement"]
    flags = ["create"]

class SpawnGroup(EventCommand):
    nid = 'spawn_group'
    tag = "unit"

    keywords = ["Group", "CardinalDirection", "StartingGroup"]
    optional_keywords = ["EntryType", "Placement"]
    flags = ["create", "no_block", 'no_follow']

class MoveGroup(EventCommand):
    nid = 'move_group'
    nickname = 'morph_group'
    tag = 'unit'

    keywords = ["Group", "StartingGroup"]
    optional_keywords = ["MovementType", "Placement"]
    flags = ['no_block', 'no_follow']

class RemoveGroup(EventCommand):
    nid = 'remove_group'
    tag = 'unit'

    keywords = ["Group"]
    optional_keywords = ["RemoveType"]

class GiveItem(EventCommand):
    nid = 'give_item'
    tag = 'unit'
    
    keywords = ["GlobalUnit", "Item"]
    flags = ['no_banner', 'no_choice', 'droppable']

class RemoveItem(EventCommand):
    nid = 'remove_item'
    tag = 'unit'
    
    keywords = ["GlobalUnit", "Item"]
    flags = ['no_banner']

class GiveMoney(EventCommand):
    nid = 'give_money'
    tag = 'general'

    keywords = ["Integer"]
    optional_keywords = ["Party"]
    flags = ['no_banner']

class GiveExp(EventCommand):
    nid = 'give_exp'
    tag = 'unit'

    keywords = ["GlobalUnit", "PositiveInteger"]

class SetExp(EventCommand):
    nid = 'set_exp'
    tag = 'unit'

    keywords = ["GlobalUnit", "PositiveInteger"]

class GiveWexp(EventCommand):
    nid = 'give_wexp'
    tag = 'unit'

    keywords = ["GlobalUnit", "WeaponType", "Integer"]
    flags = ['no_banner']

class GiveSkill(EventCommand):
    nid = 'give_skill'
    tag = 'unit'

    keywords = ["GlobalUnit", "Skill"]
    flags = ['no_banner']

class RemoveSkill(EventCommand):
    nid = 'remove_skill'
    tag = 'unit'

    keywords = ["GlobalUnit", "Skill"]
    flags = ['no_banner']

class ChangeAI(EventCommand):
    nid = 'change_ai'
    tag = 'unit'

    keywords = ["GlobalUnit", "AI"] 

class ChangeTeam(EventCommand):
    nid = 'change_team'
    tag = 'unit'
    keywords = ["GlobalUnit", "Team"]

class ChangePortrait(EventCommand):
    nid = 'change_portrait'
    tag = 'unit'
    keywords = ["GlobalUnit", "PortraitNid"]

class ChangeStats(EventCommand):
    nid = 'change_stats'
    tag = 'unit'
    keywords = ["GlobalUnit", "StatList"]
    flags = ['immediate']

class SetStats(EventCommand):
    nid = 'set_stats'
    tag = 'unit'
    keywords = ["GlobalUnit", "StatList"]
    flags = ['immediate']

class AutolevelTo(EventCommand):
    nid = 'autolevel_to'
    tag = 'unit'
    # Second argument is level that is eval'd
    keywords = ["GlobalUnit", "String"]
    # Whether to actually change the unit's level
    flags = ["hidden"]

class Promote(EventCommand):
    nid = 'promote'
    tag = 'unit'
    keywords = ["GlobalUnit"]
    optional_keywords = ["Klass"]

class ChangeClass(EventCommand):
    nid = 'change_class'
    tag = 'unit'
    keywords = ["GlobalUnit"]
    optional_keywords = ["Klass"]

class AddTag(EventCommand):
    nid = 'add_tag'
    tag = 'unit'

    keywords = ["GlobalUnit", "Tag"]

class RemoveTag(EventCommand):
    nid = 'remove_tag'
    tag = 'unit'

    keywords = ["GlobalUnit", "Tag"]

class AddTalk(EventCommand):
    nid = 'add_talk'
    tag = 'unit'

    keywords = ["Unit", "Unit"]

class RemoveTalk(EventCommand):
    nid = 'remove_talk'
    tag = 'unit'

    keywords = ["Unit", "Unit"]

class AddLore(EventCommand):
    nid = 'add_lore'
    nickname = 'unlock_lore'
    tag = 'base'

    keywords = ["Lore"]

class RemoveLore(EventCommand):
    nid = 'remove_lore'
    tag = 'base'

    keywords = ["Lore"]

class AddBaseConvo(EventCommand):
    nid = 'add_base_convo'
    tag = 'base'

    keywords = ["String"]

class IgnoreBaseConvo(EventCommand):
    nid = 'ignore_base_convo'
    tag = 'base'

    keywords = ["String"]

class RemoveBaseConvo(EventCommand):
    nid = 'remove_base_convo'
    tag = 'base'

    keywords = ["String"]

class AddMarketItem(EventCommand):
    nid = 'add_market_item'
    tag = 'base'

    keywords = ["Item"]

class RemoveMarketItem(EventCommand):
    nid = 'remove_market_item'
    tag = 'base'

    keywords = ["Item"]

class AddRegion(EventCommand):
    nid = 'add_region'
    tag = 'map'

    keywords = ["Nid", "Position", "Size", "RegionType"]
    optional_keywords = ["String"]
    flags = ["only_once"]

class RegionCondition(EventCommand):
    nid = 'region_condition'
    tag = 'map'

    keywords = ["Nid", "Condition"]

class RemoveRegion(EventCommand):
    nid = 'remove_region'
    tag = 'map'

    keywords = ["Nid"]

class ShowLayer(EventCommand):
    nid = 'show_layer'
    tag = 'map'

    keywords = ["Layer"]
    optional_keywords = ["LayerTransition"]

class HideLayer(EventCommand):
    nid = 'hide_layer'
    tag = 'map'

    keywords = ["Layer"]
    optional_keywords = ["LayerTransition"]

class AddWeather(EventCommand):
    nid = 'add_weather'
    tag = 'map'

    keywords = ["Weather"]

class RemoveWeather(EventCommand):
    nid = 'remove_weather'
    tag = 'map'

    keywords = ["Weather"]

class ChangeObjectiveSimple(EventCommand):
    nid = 'change_objective_simple'
    tag = 'general'

    keywords = ["String"]

class ChangeObjectiveWin(EventCommand):
    nid = 'change_objective_win'
    tag = 'general'
    
    keywords = ["String"]

class ChangeObjectiveLoss(EventCommand):
    nid = 'change_objective_loss'
    tag = 'general'
    
    keywords = ["String"]

class SetPosition(EventCommand):
    nid = 'set_position'
    tag = 'general'

    keywords = ["String"]

class MapAnim(EventCommand):
    nid = 'map_anim'
    tag = 'map'

    keywords = ["MapAnim", "Position"]
    flags = ["no_block"]

class ArrangeFormation(EventCommand):
    nid = 'arrange_formation'
    tag = 'general'
    # Puts units on formation tiles automatically

class Prep(EventCommand):
    nid = 'prep'
    tag = 'general'

    optional_keywords = ["Bool", "Music"]  # Pick units

class Base(EventCommand):
    nid = 'base'
    tag = 'general'

    keywords = ["Panorama"]
    optional_keywords = ["Music"]

class Shop(EventCommand):
    nid = 'shop'
    tag = 'general'

    keywords = ["Unit", "ItemList"]
    optional_keywords = ["ShopFlavor"]

class Choice(EventCommand):
    nid = 'choice'
    tag = 'general'

    keywords = ['Nid', 'String', 'StringList']  
    optional_keywords = ['Orientation']

class ChapterTitle(EventCommand):
    nid = 'chapter_title'
    tag = 'general'

    optional_keywords = ["Music", "String"]

class Alert(EventCommand):
    nid = 'alert'
    tag = 'general'

    keywords = ["String"]

class VictoryScreen(EventCommand):
    nid = 'victory_screen'
    tag = 'general'

class RecordsScreen(EventCommand):
    nid = 'records_screen'
    tag = 'general'

class LocationCard(EventCommand):
    nid = 'location_card'
    tag = 'general'

    keywords = ["String"]

class Credits(EventCommand):
    nid = 'credits'
    tag = 'general'

    keywords = ["String", "String"]
    flags = ['wait', 'center', 'no_split']

class Ending(EventCommand):
    nid = 'ending'
    tag = 'general'

    keywords = ["Portrait", "String", "String"]

class Unlock(EventCommand):
    nid = 'unlock'
    tag = 'general'

    keywords = ["Unit"]

class FindUnlock(EventCommand):
    nid = 'find_unlock'
    tag = 'general'

    keywords = ["Unit"]

class SpendUnlock(EventCommand):
    nid = 'spend_unlock'
    tag = 'general'

    keywords = ["Unit"]

class TriggerScript(EventCommand):
    nid = 'trigger_script'
    tag = 'general'

    keywords = ["Event"]
    optional_keywords = ["GlobalUnit", "GlobalUnit"]
    
def get_commands():
    return EventCommand.__subclasses__()

def restore_command(dat):
    nid, values = dat
    subclasses = EventCommand.__subclasses__()
    for command in subclasses:
        if command.nid == nid:
            copy = command(values)
            return copy
    print("Couldn't restore event command!")
    print(nid, values)
    return None

def parse_text(text):
    if text.startswith('#'):
        return Comment([text])
    arguments = text.split(';')
    command_nid = arguments[0]
    subclasses = EventCommand.__subclasses__()
    for command in subclasses:
        if command.nid == command_nid or command.nickname == command_nid:
            copy = command(arguments[1:])
            return copy
    return None

def parse(command):
    values = command.values
    num_keywords = len(command.keywords)
    true_values = values[:num_keywords]
    flags = {v for v in values[num_keywords:] if v in command.flags}
    optional_keywords = [v for v in values[num_keywords:] if v not in flags]
    true_values += optional_keywords
    return true_values, flags

from app.data.database import DB
from app.engine import item_system, item_funcs, static_random
import importlib
import logging
import copy

# === Data Creation ===

#Create a database for units and their data, to be called by unit.py at unit initialization.
def createUnitDatabase(game):
    unitDB = game.rando_settings['unitDictionary']
    unitDataDB = game.rando_settings['unitDataDictionary']
    for unit in DB.units:
        unitDB[unit.nid] = copy.deepcopy(unit)
        #Units keep track of wexp differently, make this for simplicity...
        unitDataDB[unit.nid] = UnitData()

#Create a database for classes, to track the information that changes about them (promotions, etc.)
def createClassDatabase(game):
    klassDB = game.rando_settings['klassDictionary']
    for klass in DB.classes.values():
        klassDB[klass.nid] = copy.deepcopy(klass)

#This creates the pool of classes for Players. It is saved by the Game State, as it is modified to prevent repetition of classes.
def createClassPools(game):
    num_tiers = DB.constants.value('tiers')   #So we can randomize by tier, we need to know how many there are in the game.
    class_pools = []
    lords_rando = game.rando_settings['lord_rando']
    thieves_rando = game.rando_settings['thief_rando']
    special_rando = game.rando_settings['special_rando']

    for x in range(num_tiers):   #This basically creates different pools for each tier of classes. Accounts for special settings (eg. Lords) as well
        new_pool = [c for c in DB.classes.values() if c.tier == x and not 'no_random' in c.tags]
        if not lords_rando:
            new_pool = [c for c in new_pool if not 'Lord' in c.tags]
        if not thieves_rando:
            new_pool = [c for c in new_pool if not 'Thief' in c.tags]
        if not special_rando:
            new_pool = [c for c in new_pool if not 'Special' in c.tags]
        new_pool = [c.nid for c in new_pool]
        #logging.debug("Created Pool for Tier %s: %s", x, new_pool)
        class_pools.append(new_pool)
    return class_pools

#Used to refresh the list of classes used by player units.
def refreshClassPool(tier, game):
    lords_rando = game.rando_settings['lord_rando']
    thieves_rando = game.rando_settings['thief_rando']
    special_rando = game.rando_settings['special_rando']
    new_pool = [c for c in DB.classes.values() if c.tier == tier and not 'no_random' in c.tags]
    if not lords_rando:
        new_pool = [c for c in new_pool if not 'Lord' in c.tags]
    if not thieves_rando:
        new_pool = [c for c in new_pool if not 'Thief' in c.tags]
    if not special_rando:
        new_pool = [c for c in new_pool if not 'Special' in c.tags]
    new_pool = [c.nid for c in new_pool]
    return new_pool

# === Class Randomization ===

#This is called at file start. This performs the randomization of Players, Bosses and Others, before the game begins.
def randomizeClassStatic(game):
    unitDB = game.rando_settings['unitDictionary']
    genericDB = game.rando_settings['genericDictionary']
    pools = game.rando_settings['class_pools']
    units_to_rando = []
    num_tiers = DB.constants.value('tiers')
    generic_pool = [[] for _ in range(num_tiers)]

    #Create generic class pools. They need their own pool since there's no repetition check.
    for x in range(num_tiers):
        generic_pool[x] = [c for c in DB.classes.values() if c.tier == x and not 'no_random' in c.tags]
        for klass in generic_pool[x]:
            if (not game.rando_settings['lord_rando'] and 'Lord' in klass.tags) or (not game.rando_settings['thief_rando'] and 'Thief' in klass.tags) or (not game.rando_settings['special_rando'] and 'Special' in klass.tags):
                generic_pool[x].remove(klass)
        generic_pool[x] = [c.nid for c in generic_pool[x]]
        logging.debug("Created generic pool for Tier %s: %s", x, generic_pool[x])

    #Get units into a dictionary. This will be called by unit.py to alter a unit during runtime.
    for unit in DB.units:
        if not 'no_random' in unit.tags:
            if (not game.rando_settings['lord_rando'] and 'Lord' in unit.tags) or (not game.rando_settings['thief_rando'] and 'Thief' in unit.tags) or (not game.rando_settings['special_rando'] and 'Special' in unit.tags):
                continue
            else:
                units_to_rando.append(unit)

    #Randomize defined unit classes
    while len(units_to_rando) > 0:
        int1 = static_random.get_randint(0, len(units_to_rando) - 1)
        unit_to_pick = units_to_rando[int1]
        klass = unit_to_pick.klass
        tier = DB.classes.get(klass).tier
        if 'Player' in unit_to_pick.tags:
            #Refresh the class pool if needed
            if len(pools[tier]) == 0:
                refreshClassPool(tier, game)
            int2 = static_random.get_randint(0, len(pools[tier]) - 1)
            class_to_pick = pools[tier][int2]
            unitDB[unit_to_pick.nid].klass = class_to_pick
            #Remove the class from the pool, but only if we're preventing redundancy
            if game.rando_settings['player_class_stop_redundancy']:
                pools[tier].remove(class_to_pick)
        #Bosses/Others also use generic pool
        else:
            int2 = static_random.get_randint(0, len(generic_pool[tier]) - 1)
            class_to_pick = generic_pool[tier][int2]
            unitDB[unit_to_pick.nid].klass = class_to_pick
        #We're done with this unit, so remove them from the pool
        #logging.debug("%s's new class is: %s", unit_to_pick.name, unit_to_pick.klass)
        units_to_rando.remove(unit_to_pick)

    #Randomize Generic Unit Classes. Generics can have the same nid, so we need to go by level, and then by unit. Dynamically created units will bypass randomization.
    for level in DB.levels.values():
        for unit in level.units:
            if unit.generic:
                if not unit.nid in genericDB[level.nid]:
                    genericDB[level.nid][unit.nid] = copy.deepcopy(unit)
                tier = DB.classes.get(unit.klass).tier
                int3 = static_random.get_randint(0, len(generic_pool[tier]) - 1)
                class_to_pick = generic_pool[tier][int3]
                genericDB[level.nid][unit.nid].klass = class_to_pick


#This alters weapon exp to match the new class. Only applies to named units, generic units are handled differently.
def randomizeWexpStatic(game):
    unitDB = game.rando_settings['unitDictionary']
    unitDataDB = game.rando_settings['unitDataDictionary']
    klassDB = game.rando_settings['klassDictionary']
    units_to_rando = []

    #Get eligible units
    for unit in unitDB.values():
        if not 'no_random' in unit.tags:
            #This may be a redundant check, figure it out later
            if (not game.rando_settings['lord_rando'] and 'Lord' in unit.tags) or (not game.rando_settings['thief_rando'] and 'Thief' in unit.tags) or (not game.rando_settings['special_rando'] and 'Special' in unit.tags):
                continue
            else:
                units_to_rando.append(unit)

    for unit in units_to_rando:
        newWexp = {weapon_nid: 0 for weapon_nid in DB.weapons.keys()}
        #Get the unit's default wexp
        weapon_gain = unit.wexp_gain
        wexp = {weapon_nid: weapon_gain.get(weapon_nid, DB.weapons.default()).wexp_gain for weapon_nid in DB.weapons.keys()}

        #Determine which weapons our new class has
        klassObj = klassDB.get(unit.klass)
        klass_weapon_gain = klassObj.wexp_gain
        validWeps = []
        for weapon in DB.weapons.keys():
            if klass_weapon_gain.get(weapon).wexp_gain > 0:
                validWeps.append(weapon)
        logging.debug("%s's new class weapons: %s", unit.nid, validWeps)

        #Determine what the maximum value a weapon rank can be for this game
        wepRanks = sorted(DB.weapon_ranks, key=lambda x: x.requirement)
        biggest = 0
        for rank in wepRanks:
            if rank.requirement > biggest:
                biggest = rank.requirement

        randomMode = game.rando_settings['wexp_mode']
        if validWeps:
            if randomMode == 'Similar':   #Similar - Basically just moves ranks around.
                wexpAmounts = []
                oldWeaponCount = 0
                for amount in wexp.values():   #Collect each weapon rank value from the character's default. Also, keep track of how many weapons old class had.
                    if amount > 0:
                        wexpAmounts.append(amount)
                        oldWeaponCount += 1
                if len(validWeps) < oldWeaponCount:   #We have fewer weapons now, so some weapons will get a boost
                    while len(wexpAmounts) > 0:
                        toPick = static_random.get_randint(0, len(wexpAmounts) - 1)
                        pick = wexpAmounts[toPick]
                        fill = validWeps[static_random.get_randint(0, len(validWeps) - 1)]
                        newWexp[fill] += pick
                        wexpAmounts.pop(toPick)
                else:                                 #We have equal or more weapons now, so evenly redistribute. Any that don't get filled will be defaulted to 1.
                    while len(wexpAmounts) > 0:
                        toPick = static_random.get_randint(0, len(wexpAmounts) - 1)
                        pick = wexpAmounts[toPick]
                        toFill = static_random.get_randint(0, len(validWeps) - 1)
                        fill = validWeps[toFill]
                        newWexp[fill] += pick
                        wexpAmounts.pop(toPick)
                        validWeps.pop(toFill)
                for weapon in validWeps:   #We have more weapons than we used to, so allow the extras to become usable. Also clamp to max if above it.
                    if newWexp[weapon] < 1:
                        newWexp[weapon] = 1
                    elif newWexp[weapon] > biggest:
                        newWexp[weapon] = biggest
            elif randomMode == 'Redistribute':   #Redistribute - Takes full amount of WXP unit has and distributes it randomly
                wexpAmount = 0
                for amount in wexp.values():   #Just lump all old WEXP into a big sum
                    wexpAmount += amount
                while wexpAmount > 0:          #Pick one weapon at random that we have, and give it a point. Repeat until no points left.
                    toFill = static_random.get_randint(0, len(validWeps) - 1)
                    fill = validWeps[toFill]
                    newWexp[fill] += 1
                    wexpAmount -= 1
                for weapon in validWeps:  # If anything we need is at 0, make it usable
                    if newWexp[weapon] < 1:
                        newWexp[weapon] = 1
                    elif newWexp[weapon] > biggest:
                        newWexp[weapon] = biggest
            elif randomMode == 'Absolute':      #Absolute - Weapon ranks will randomize to any valid value
                for weapon in validWeps:
                    newWexp[weapon] = static_random.get_randint(1, biggest)
        unitDataDB[unit.nid].wexp = {weapon: value for weapon, value in newWexp.items()}
        logging.debug("%s's new WEXP: %s", unit.nid, newWexp)

#If we've randomized classes, then we'll need to update the starting inventories to match new weapon ranks. This version is for named units.
def randomizeWeaponsStatic(game):
    #Check if items have been randomized, and use new Dictionary if needed
    if game.rando_settings['item_rando']:
        item_pool = game.rando_settings['itemDictionary']
    else:
        item_pool = DB.items

    #Get eligible units
    unitDB = game.rando_settings['unitDictionary']
    unitDataDB = game.rando_settings['unitDataDictionary']
    units_to_rando = []
    for unit in unitDB.values():
        if not 'no_random' in unit.tags:
            #Again, this may end up redundant. Shouldn't hurt to leave it for now though
            if (not game.rando_settings['lord_rando'] and 'Lord' in unit.tags) or (not game.rando_settings['thief_rando'] and 'Thief' in unit.tags) or (not game.rando_settings['special_rando'] and 'Special' in unit.tags):
                continue
            else:
                units_to_rando.append(unit)

    #Set this up beforehand. Needed in case we need to force a switch to Random mode.
    fallback = False

    #This is where the new weapons are selected and assigned. Note that only weapons and spells are affected, other items are ignored.
    for unitPrefab in units_to_rando:
        itemsToAdd = []
        unitWexp = unitDataDB[unitPrefab.nid].wexp
        #We need a unit object, not a UnitPrefab. We'll create a faker for the purposes of the item functions we need.
        unit = SpoofUnit(unitPrefab)
        unit.wexp = unitWexp
        items = unit.items  #This is a list of Tuples, format (Item Name, Droppable Flag)
        for itemTuple in items:
            originalItem = itemTuple
            #Similar to units, we need an Item object as well. Would really like a better method then spamming object instantiations though...
            item = item_funcs.create_item(unit, originalItem[0], originalItem[1])
            if item_system.is_weapon(unit, item) or item_system.is_spell(unit, item):
                if game.rando_settings['keepWeps'] and item_funcs.available(unit, item):   #If we can still use it after class rando, and setting is enabled, leave it alone
                    continue
                else:
                    if game.rando_settings['weps_mode'] == 'Match': #Try to have new weapons match the ranks of the old ones. Tends to have issues in some circumstances (ex. Vanilla FE8 has no E rank Dark, etc.)
                        #I don't really have a good way to deal with crap like monster claws and generic spells. Just include them for now and let devs find ways to filter
                        validWeps = ['Neutral']
                        rank_needed = 0
                        fallback = False
                        wepRanks = sorted(DB.weapon_ranks, key=lambda x: x.requirement)
                        for rank in wepRanks:     #Get the numeric wexp the weapon needs. We need to check if we can still wield this with any weapon we can access.
                            if item_system.weapon_rank(unit, item) == rank.rank:
                                rank_needed = rank.requirement
                        for weapon, value in unitWexp.items():     #Check our WEXP. See if we have any weapon types that can use a weapon of this rank.
                            if value >= rank_needed:
                                validWeps.append(weapon)
                        if item_system.weapon_rank(unit, item) is None: #The item has no weapon rank. We can't match, so fallback to random logic.
                            fallback = True
                        if validWeps and not fallback:   #If there's a valid rank, start looking for a weapon to use.
                            newWepOptions = []
                            for wep in item_pool:
                                check = 0
                                if any(component.nid == 'weapon' or component.nid == 'spell' for component in wep.components):
                                    for component in wep.components:
                                        if component.nid == 'weapon_type' and component.weapon_type(unit, wep) in validWeps:   #Is the weapon type one our class can wield?
                                            check += 1
                                        if component.nid == 'weapon_rank' and component.weapon_rank(unit, wep) == item_system.weapon_rank(unit, item):   #Is it the same rank as the existing item?
                                            check += 1
                                        if component.nid == 'prf_class' or component.nid == 'prf_tag' or component.nid == 'prf_unit':  # Add these to the pool anyway, if they can't be valid they'll just fail the check regardless
                                            check += 2
                                    if check >= 2:   #If enough of the above were true, this is a weapon of matching rank (or a special case), and thus is an option for replacement.
                                        newWepOptions.append(wep)
                            if len(newWepOptions) > 0:
                                while len(newWepOptions) > 0:
                                    toPick = static_random.get_randint(0, len(newWepOptions) - 1)
                                    selectedWep = item_funcs.create_item(unit, newWepOptions[toPick].nid, item.droppable)
                                    if item_funcs.available(unit, selectedWep):   #We can use it, so prepare to add it to the unit.
                                        logging.debug("The new weapon is: %s, giving to %s the %s", selectedWep.name, unit.name, unit.klass)
                                        itemsToAdd.append([newWepOptions[toPick].nid, originalItem[1]])
                                        break
                                    else:   #For whatever reason, we can't use it (Tag/Class lock, etc.). Remove it from the options and try again.
                                        newWepOptions.pop(toPick)
                            else:   #We found nothing that matches the criteria, fall back to Random logic
                                fallback = True
                    if game.rando_settings['weps_mode'] == 'Random' or fallback:
                        #Just for debugging purposes
                        if game.rando_settings['weps_mode'] == 'Match':
                            logging.debug("Falling back to random logic")
                        validWeps = []
                        newWepOptions = []
                        for weapon, value in unitWexp.items():     #Get which weapons we can use, so we can filter the database.
                            if value >= 0:
                                validWeps.append(weapon)
                        #Determine which weapons we can choose from
                        for wep in item_pool:
                            if any(component.nid == 'weapon' or component.nid == 'spell' for component in wep.components):
                                #if not any(component.nid == 'weapon_rank' or component.nid == 'no_random_give' for component in wep.components): #Add custom setting to ignore special items later
                                    #continue
                                #The blast stuff was to block certain crashes, not sure if those were rando related or engine bugs. May need to be experimented with more.
                                if not any (component.nid in ['weapon_type','weapon_rank','prf_class','prf_tag','prf_unit'] for component in wep.components) or any(component.nid in ['enemy_blast_aoe', 'equation_blast_aoe'] for component in wep.components):
                                    continue
                                option = item_funcs.create_item(None, wep.nid, item.droppable)
                                if item_funcs.available(unit, option):
                                    newWepOptions.append(option)
                        #Add our new weapon, so we can give to the unit later
                        if newWepOptions:
                            selectedWep = newWepOptions[static_random.get_randint(0, len(newWepOptions) - 1)]
                            itemsToAdd.append([selectedWep.nid, originalItem[1]])
            else:
                #We couldn't get a new item, so just use the vanilla one. This will always occur for items like Vulneraries, Promo items, etc.
                itemsToAdd.append([item.nid, originalItem[1]])

        #Actually add the new item list to the unit data. Will be assigned at unit initialization in unit.py
        unitDB[unit.nid].items = itemsToAdd
        logging.debug("New items for %s: %s", unit.name, itemsToAdd)

#Similar to above, but with some changes. Explicitly for generic units, as they play by different rules.
def randomizeGenericWeaponsStatic(game):
    #Check if items have been randomized, and use new Dictionary if needed
    if game.rando_settings['item_rando']:
        item_pool = game.rando_settings['itemDictionary']
    else:
        item_pool = DB.items
    genericDB = game.rando_settings['genericDictionary']
    klassDB = game.rando_settings['klassDictionary']

    #items = unit.items
    #oldWexp = copy.copy(unit.wexp)

    for levelId in genericDB.keys():
        for unitPrefab in genericDB[levelId].values():
            itemsToAdd = []
            fallback = False
            maxRank = 0
            unit = SpoofUnit(unitPrefab, klassDB, True)
            klass = unit.klass
            klassObj = klassDB.get(klass)
            items = unitPrefab.starting_items
            #Generics use their class's default Wexp, and then pump up the numbers to match their inventories. The latter part doesn't matter here though.
            weapon_gain = klassObj.wexp_gain
            unit.wexp = {weapon_nid: weapon_gain.get(weapon_nid, DB.weapons.default()).wexp_gain for weapon_nid in DB.weapons.keys()}
            oldWexp = copy.copy(unit.wexp)

            for itemTuple in items:
                item = item_funcs.create_item(unit, itemTuple[0], itemTuple[1])
                if item_system.is_weapon(unit, item) or item_system.is_spell(unit, item):
                    weapon_rank_required = item_system.weapon_rank(unit, item)
                    if weapon_rank_required:
                        requirement = DB.weapon_ranks.get(weapon_rank_required).requirement
                        if requirement > maxRank:
                            maxRank = requirement

            for itemTuple in items:
                item = item_funcs.create_item(unit, itemTuple[0], itemTuple[1])
                if item_system.is_weapon(unit, item) or item_system.is_spell(unit, item):
                    if game.rando_settings['keepWeps'] and item_funcs.available(unit, item):   #If we can still use it after class rando, and setting is enabled, leave it alone
                        continue
                    else:
                        if game.rando_settings['weps_mode'] == 'Match':
                            validWeps = []
                            fallback = False
                            for weapon, value in unit.wexp.items():     #Check our WEXP. See if we have any weapon types that can use a weapon of this rank.
                                if value > 0:
                                    validWeps.append(weapon)
                            validWeps.append('Neutral')
                            if validWeps:   #If there's a valid rank, start looking for a weapon to use.
                                newWepOptions = []
                                for wep in item_pool:
                                    check = 0
                                    if any(component.nid == 'weapon' or component.nid == 'spell' for component in wep.components):
                                        for component in wep.components:
                                            if component.nid == 'weapon_type' and component.weapon_type(unit, wep) in validWeps:   #Is the weapon type one our class can wield?
                                                check += 1
                                            if component.nid == 'weapon_rank' and component.weapon_rank(unit, wep) == item_system.weapon_rank(unit, item):   #Is it the same rank as the existing item?
                                                check += 1
                                            if component.nid == 'prf_class' or component.nid == 'prf_tag' or component.nid == 'prf_unit': #Add these to the pool anyway, if they can't be valid they'll just fail the check regardless
                                                check += 2
                                        if check >= 2:   #If both of the above were true, this is a weapon of matching rank, and thus is an option for replacement.
                                            newWepOptions.append(wep)
                                if len(newWepOptions) > 0:
                                    while len(newWepOptions) > 0:
                                        toPick = static_random.get_randint(0, len(newWepOptions) - 1)
                                        selectedWep = item_funcs.create_item(unit, newWepOptions[toPick].nid, item.droppable)
                                        unit.wexp = {weapon_nid: 99999 for weapon_nid in DB.weapons.keys()} #Sucky code, but we need to make wexp a non-factor before using Available
                                        if item_funcs.available(unit, selectedWep):   #We can use it, so prepare to add it to the unit.
                                            logging.debug("The new weapon is: %s, giving to %s the %s", selectedWep.name, unit.name, unit.klass)
                                            itemsToAdd.append([newWepOptions[toPick].nid, itemTuple[1]])
                                            unit.wexp = oldWexp
                                            break
                                        else:   #For whatever reason, we can't use it (Tag/Class lock, etc.). Remove it from the options and try again.
                                            newWepOptions.pop(toPick)
                                        unit.wexp = oldWexp
                                else:   #We found nothing that matches the criteria, fall back to Random logic
                                    fallback = True
                        if game.rando_settings['weps_mode'] == 'Random' or fallback:
                            validWeps = []
                            newWepOptions = []
                            for weapon, value in unit.wexp.items():     #Get which weapons we can use, so we can filter the database.
                                if value > 0:
                                    validWeps.append(weapon)
                            for wep in item_pool:
                                if any(component.nid == 'weapon' or component.nid == 'spell' for component in wep.components):
                                    #if not any(component.nid == 'weapon_rank' or component.nid == 'no_random_give' for component in wep.components): #Add custom setting to ignore special items later
                                        #continue
                                    if not any (component.nid in ['weapon_type','weapon_rank','prf_class','prf_tag','prf_unit'] for component in wep.components) or any(component.nid in ['enemy_blast_aoe', 'equation_blast_aoe'] for component in wep.components):
                                        continue
                                    option = item_funcs.create_item(None, wep.nid, item.droppable)
                                    weapon_rank_required = item_system.weapon_rank(unit, option)
                                    if weapon_rank_required:
                                        requirement = DB.weapon_ranks.get(weapon_rank_required).requirement
                                    else:
                                        requirement = 0
                                    unit.wexp = {weapon_nid: 99999 for weapon_nid in DB.weapons.keys()}
                                    if requirement <= maxRank and item_funcs.available(unit, option):
                                        newWepOptions.append(option)
                                    unit.wexp = oldWexp
                            if newWepOptions:
                                selectedWep = newWepOptions[static_random.get_randint(0, len(newWepOptions) - 1)]
                                itemsToAdd.append([newWepOptions[selectedWep].nid, itemTuple[1]])
                else:
                    itemsToAdd.append([item.nid, itemTuple[1]])

            genericDB[levelId][unit.nid].items = itemsToAdd
            #logging.debug("New items for %s: %s", unit.name, itemsToAdd)

#Randomizes each classes's promotion options.
def randomizePromotions(game):
    klassDB = game.rando_settings['klassDictionary']
    num_tiers = DB.constants.value('tiers')  # So we can randomize by tier, we need to know how many there are in the game.
    promo_options = [[] for _ in range(num_tiers)]
    promo_options_tracker = [[] for _ in range(num_tiers)]
    eligible_classes = [[] for _ in range(num_tiers)]
    promo_dict = {klass.nid: [] for klass in klassDB.values()}
    promo_amount = game.rando_settings['promotion_amount']

    #Create full lists of Classes that can promote, as well as promoted classes. Organize by tier.
    for x in range(num_tiers):
        promo_options[x] = [c for c in klassDB.values() if c.tier == x and (c.promotes_from or 'r_promote_include' in c.tags) and not 'r_no_promote_to' in c.tags]
        for klass in promo_options[x]:
            if (not game.rando_settings['lord_rando'] and 'Lord' in klass.tags) or (not game.rando_settings['thief_rando'] and 'Thief' in klass.tags) or (not game.rando_settings['special_rando'] and 'Special' in klass.tags):
                promo_options[x].remove(klass)

        eligible_classes[x] = [c for c in klassDB.values() if c.tier == x and c.turns_into and not 'r_no_promote_from' in c.tags]
        for klass in eligible_classes[x]:
            if (not game.rando_settings['lord_rando'] and 'Lord' in klass.tags) or (not game.rando_settings['thief_rando'] and 'Thief' in klass.tags) or (not game.rando_settings['special_rando'] and 'Special' in klass.tags):
                eligible_classes[x].remove(klass)

        #If we're doing full random, this list will suffice as the redundancy tracker. Match mode is messier.
        if game.rando_settings['promotion_mode'] == 'Random':
            promo_options_tracker[x] = [c for c in promo_options[x]]
            #promo_options_tracker[x] = [c for c in klassDB.values() if c.tier == x and (c.promotes_from or 'r_promote_include' in c.tags) and not 'r_no_promote_to' in c.tags]

    #Get a list of all weapon types
    weapons = [weapon_nid for weapon_nid in DB.weapons.keys()]

    #For each weapon type, create a set of pools by tier, with every class in that tier that uses that weapon type. This is only used for match mode.
    class_pools_by_weapon = {weapon_nid : [[] for _ in range(num_tiers)] for weapon_nid in DB.weapons.keys()}
    for weapon in weapons:
        for x in range(num_tiers):
            for klass in promo_options[x]:
                weapon_gain = klass.wexp_gain
                wexp_value = weapon_gain.get(weapon, DB.weapons.default()).wexp_gain
                if wexp_value > 0:
                    pool_to_use = class_pools_by_weapon.get(weapon)
                    pool_to_use[x].append(klass)

    #This is where the assignment occurs
    for x in range(num_tiers):
        while len(eligible_classes[x]) > 0:
            to_pick = static_random.get_randint(0, len(eligible_classes[x]) - 1)
            klass = eligible_classes[x][to_pick]
            #logging.debug("Randomizing Promotions for: %s", klass.name)

            #This is a failsafe, for when things just can't work (ex. Game set to have 3 promos for everyone, but only 2 promoted classes use bows, etc.)
            retry = 3

            while retry > 0:
                weapon_exp = klass.wexp_gain
                available_weps = []
                class_choices = []

                #Determine which weapons our current class can use
                for weapon in weapons:
                    amount = weapon_exp.get(weapon).wexp_gain
                    if amount > 0:
                        available_weps.append(weapon)

                #Start building options list
                for promo_klass in promo_options[x+1]:
                    promo_wexp = promo_klass.wexp_gain
                    promo_weps = []
                    not_used = False

                    #Find out which weapons this promoted class can use
                    for weapon in weapons:
                        amount = promo_wexp.get(weapon).wexp_gain
                        if amount > 0:
                            promo_weps.append(weapon)

                    #Check if this class has not been used yet
                    if game.rando_settings['promotion_mode'] == 'Random':
                        if promo_klass in promo_options_tracker[x+1]:
                            not_used = True
                    else:
                        for weapon in promo_weps:
                            list_to_check = class_pools_by_weapon.get(weapon)
                            if promo_klass in list_to_check[x+1]:
                                not_used = True

                    #If the promoted class is available and shares a weapon with the base class, make it available to select (if random mode, just add it)
                    if not_used:
                        if game.rando_settings['promotion_mode'] == 'Random':
                            class_choices.append(promo_klass)
                        else:
                            for weapon in available_weps:
                                if weapon in promo_weps:
                                    class_choices.append(promo_klass)
                                    break
                #logging.debug("Here are our options: %s", [c.nid for c in class_choices])

                if class_choices:
                    #Remove duplicates
                    for dupe in class_choices:
                        if dupe.nid in promo_dict.get(klass.nid):
                            class_choices.remove(dupe)

                    #Do we have enough choices to satisfy the requirements? If so, randomly assign them and remove them from the pools, and stop the loop.
                    if len(class_choices) >= (promo_amount - len(promo_dict.get(klass.nid))):
                        retry = 0
                        while len(promo_dict.get(klass.nid)) < promo_amount:
                            #Pick a class at random, and add it to the promotion dictionary
                            new_promo_int = static_random.get_randint(0, len(class_choices) - 1)
                            new_promo = class_choices[new_promo_int]
                            promo_dict.get(klass.nid).append(new_promo.nid)
                            #Update the promoted klass's promote from data, needed for class skills. Will get overwritten, but will still match one of the randomized classes.
                            klassDB[new_promo.nid].promotes_from = klass.nid
                            #Remove it from choices so we don't pick it again
                            class_choices.remove(new_promo)
                            logging.debug("%s can now promote to %s", klass.name, new_promo.name)

                            # Prevent redundancy by removing the class from the pool, if we care about redundancy
                            if game.rando_settings['promo_rando_stop_redundancy']:
                                if game.rando_settings['promotion_mode'] == 'Random':
                                    promo_options_tracker[x+1].remove(new_promo)
                                else:
                                    for wep in weapons:
                                        list_to_edit = class_pools_by_weapon.get(wep)
                                        if new_promo in list_to_edit[x+1]:
                                            list_to_edit[x+1].remove(new_promo)

                    #We do not, so add any existing choices and refresh the pools. Then, try again for the remainder.
                    else:
                        for choice in class_choices:
                            promo_dict.get(klass.nid).append(choice.nid)
                            # Update the promoted klass's promote from data, needed for class skills. Will get overwritten, but will still match one of the randomized classes.
                            klassDB[choice.nid].promotes_from = klass.nid
                            logging.debug("%s can now promote to %s", klass.name, choice.name)

                            # Prevent redundancy by removing the class from the pool
                            if game.rando_settings['promo_rando_stop_redundancy']:
                                if game.rando_settings['promotion_mode'] == 'Random':
                                    promo_options_tracker[x+1].remove(choice)
                                else:
                                    for wep in weapons:
                                        list_to_edit = class_pools_by_weapon.get(wep)
                                        if choice in list_to_edit[x+1]:
                                            list_to_edit[x+1].remove(choice)

                        #Refresh the pool
                        if game.rando_settings['promotion_mode'] == 'Random':
                            logging.debug("Refreshing the promotion pool, mode is Random")
                            promo_options_tracker[klass.tier + 1] = [c for c in promo_options[klass.tier + 1]]
                            #promo_options_tracker[klass.tier + 1] = [c for c in DB.classes.values() if c.tier == klass.tier + 1 and (c.promotes_from or 'r_promote_include' in c.tags) and not 'r_no_promote_to' in c.tags]
                        else:
                            for wep_type in available_weps:
                                logging.debug("Refreshing tier %s %s pool", klass.tier + 1, wep_type)
                                for promoKlass in promo_options[klass.tier + 1]:
                                    klass_weapon_gain = promoKlass.wexp_gain
                                    klass_wexp_value = klass_weapon_gain.get(wep_type, DB.weapons.default()).wexp_gain
                                    if klass_wexp_value > 0:
                                        pool_to_refresh = class_pools_by_weapon.get(wep_type)
                                        pool_to_refresh[klass.tier + 1].append(promoKlass)
                        retry -= 1

                #We had no choices available, so refresh the pools in question and try this class again
                else:
                    if game.rando_settings['promotion_mode'] == 'Random':
                        logging.debug("Refreshing the promotion pool, mode is Random")
                        promo_options_tracker[klass.tier + 1] = [c for c in DB.classes.values() if c.tier == klass.tier + 1 and (c.promotes_from or 'r_promote_include' in c.tags) and not 'r_no_promote_to' in c.tags]
                    else:
                        for wep_type in available_weps:
                            logging.debug("Refreshing tier %s %s pool", klass.tier + 1, wep_type)
                            for promoKlass in promo_options[klass.tier + 1]:
                                klass_weapon_gain = promoKlass.wexp_gain
                                klass_wexp_value = klass_weapon_gain.get(wep_type, DB.weapons.default()).wexp_gain
                                if klass_wexp_value > 0:
                                    pool_to_refresh = class_pools_by_weapon.get(wep_type)
                                    pool_to_refresh[klass.tier + 1].append(promoKlass)
                    retry -= 1

                #Whether it got enough promotion options or not, this class is now finished. Update dictionary, remove class and work on the next one.
                if retry == 0:
                    #If we got literally nothing (REVENANT), use the class's default for safety
                    if not promo_dict[klass.nid] and klass.turns_into:
                        #promo_dict[klass.nid] = klass.turns_into
                        logging.debug("Could not randomize, falling back to default: %s", klass.turns_into)
                    klassDB[klass.nid].turns_into = promo_dict[klass.nid]
                    eligible_classes[x].remove(klass)

# === Stat Randomization ===

#This handles the randomization of base stats. Both redistribution and Delta types are available.
def randomizeBasesStatic(game):
    extra_stats = []
    count = 0
    for stat_nid in DB.stats.keys():  #Need to account for stats we don't want to randomize here, and learn their positions
        if stat_nid in ['CON','MOV']:
            extra_stats.append(count)
        count += 1

    unitDB = game.rando_settings['unitDictionary']
    unitDataDB = game.rando_settings['unitDataDictionary']
    units_to_rando = []
    #Don't need to check for Lords, etc. All units are eligible, unit.py will determine if they get new bases.
    for unit in unitDB.values():
        if not 'no_random' in unit.tags:
            units_to_rando.append(unit)
    for unit in units_to_rando:
        preBases = unit.bases
        bases = {stat_nid: preBases.get(stat_nid, 0) for stat_nid in DB.stats.keys()}
        total_bst = 0
        new_bases = {stat_nid: 0 for stat_nid in DB.stats.keys()}
        #logging.debug("Stats DB: %s", DB.stats.items())

        if 'CON' in DB.stats.keys():  #Special stats treated separately, just copy them as they are for now
            new_bases['CON'] = bases['CON']
        if 'MOV' in DB.stats.keys():
            new_bases['MOV'] = bases['MOV']
        randomMode = game.rando_settings['bases_mode']
        variance = game.rando_settings['bases_variance']
        stats = [stat_name for stat_name in DB.stats.keys()]

        if randomMode == 'Redistribute':   #Take our total BST and redistribute it, with a 3:1 bias towards HP.
            total_variance = static_random.get_randint(-variance, variance)
            for stat, amount in bases.items():   #CON and MOV are handled separately
                if stat in extra_stats:
                    continue
                total_bst += bases[stat]
            total_bst += total_variance
            #logging.debug("New total BST: %s", total_bst)
            while total_bst > 0:
                which_stat = static_random.get_randint(0, len(DB.stats) + 1) #Get stat position, and add 2 more positions to add an HP bias
                if which_stat in [0, len(DB.stats), len(DB.stats) + 1]:
                    to_increase = stats[0]
                    new_bases[to_increase] += 1
                    total_bst -= 1
                elif which_stat in extra_stats:  #Just ignore special stats, reroll
                     continue
                else:
                    to_increase = stats[which_stat]
                    new_bases[to_increase] += 1
                    total_bst -= 1
        elif randomMode == 'Delta':   #Base stat is modified within a specified variance
            for stat in bases:   #CON and MOV are handled separately
                if stat in extra_stats:
                    continue
                amount_to_add = static_random.get_randint(-variance, variance)
                new_bases[stat] = bases[stat] + amount_to_add
                if new_bases[stat] < 0:
                    new_bases[stat] = 0
        hp_stat = stats[0]  #We just have to assume that the first stat is HP or an HP equivalent
        if new_bases[hp_stat] < 1:  # If the character somehow got no HP, give them 1 HP. RIP this character XD
            new_bases[hp_stat] = 1

        unitDataDB[unit.nid].bases = new_bases


def randomizeGrowthsStatic(game):
    extra_stats = []
    count = 0
    for stat_nid in DB.stats.keys():  # Need to account for stats we don't want to randomize here, and learn their positions
        if stat_nid in ['CON', 'MOV']:
            extra_stats.append(count)
        count += 1

    unitDB = game.rando_settings['unitDictionary']
    unitDataDB = game.rando_settings['unitDataDictionary']
    units_to_rando = []
    # Don't need to check for Lords, etc. All units are eligible, unit.py will determine if they get new growths.
    for unit in unitDB.values():
        if not 'no_random' in unit.tags:
            units_to_rando.append(unit)
    for unit in units_to_rando:
        preGrowths = unit.growths
        growths = {stat_nid: preGrowths.get(stat_nid, 0) for stat_nid in DB.stats.keys()}
        tgr = 0
        new_growths = {stat_nid: 0 for stat_nid in DB.stats.keys()}
        if 'CON' in DB.stats.keys():  #Special stats treated separately, just copy them as they are for now
            new_growths['CON'] = growths['CON']
        if 'MOV' in DB.stats.keys():
            new_growths['MOV'] = growths['MOV']
        randomMode = game.rando_settings['growths_mode']
        variance = game.rando_settings['growths_variance']
        stats = [stat_name for stat_name in DB.stats.keys()]

        if randomMode == 'Redistribute':   #Take our total growth rates and redistribute them, with a 3:1 bias towards HP.
            total_variance = static_random.get_randint(-variance, variance)
            for stat in growths:   #CON and MOV are handled separately
                if stat in extra_stats:
                    continue
                tgr += growths[stat]
            tgr += total_variance
            #logging.debug("New TGR: %s", tgr)
            while tgr > 0:
                which_stat = static_random.get_randint(0, len(DB.stats) + 1)
                if which_stat in [0, len(DB.stats), len(DB.stats) + 1]:
                    if tgr >= 5:
                        new_growths['HP'] += 5   #Keeping growths neatly in intervals of 5 like vanilla, while accounting for weird growth rates
                    else:
                        new_growths['HP'] += tgr
                elif which_stat in extra_stats:  #Just ignore special stats, reroll
                     continue
                else:
                    to_increase = stats[which_stat]
                    if tgr >= 5:
                        new_growths[to_increase] += 5
                    else:
                        new_growths[to_increase] += tgr
                tgr -= 5
        elif randomMode == 'Delta':   #Growth is modified within a specified variance
            for stat in growths:   #CON and MOV are handled separately
                if stat in extra_stats:
                    continue
                amount_to_add = static_random.get_randint(-variance, variance)
                new_growths[stat] = growths[stat] + amount_to_add
                if new_growths[stat] < 0:
                    new_growths[stat] = 0
        elif randomMode == 'Absolute':
            for stat in new_growths:
                if stat in extra_stats:
                    continue
                new_growths[stat] = static_random.get_randint(game.rando_settings['growths_min'], game.rando_settings['growths_max'])

        unitDataDB[unit.nid].growths = new_growths

# === Item Randomization ===

def createRandomItemDictionary(game):
    newDic = copy.deepcopy(DB.items)
    #A dev will need to edit this to accommodate whatever weapons they wish to designate as "safe"
    safe_weapons = ['Iron Sword', 'Iron Lance', 'Iron Axe', 'Iron Bow', 'Fire', 'Lightning', 'Flux']
    mode = game.rando_settings['random_effects_mode']
    effect_limit = game.rando_settings['random_effects_limit']
    validComponents = game.rando_settings['weapon_properties']
    effectiveTags = game.rando_settings['weapon_effective']
    equipSkills = game.rando_settings['weapon_imbue']
    statusSkills = game.rando_settings['weapon_inflict']
    #A dev may also need to edit this to determine which components are allowed to be removed from weapons
    all_properties = ['brave','lifelink','reaver','cannot_counter','cannot_be_countered','magic','effective','effective_tag','status_on_equip','status_on_hold','status_on_hit']

    for item in newDic:
        specialComponents = [component.nid for component in item.components if component.nid in all_properties]
        if not any(component.nid == 'no_random' for component in item.components):
            #This first part is for weapon stats. Also works for spells.
            for component in item.components:
                if game.rando_settings['wepMt'] and component.nid == 'damage':
                    variance = static_random.get_randint(-game.rando_settings['wepMtVar'],game.rando_settings['wepMtVar'])
                    component.value += variance
                    if component.value < game.rando_settings['wepMtMin']:
                        component.value = game.rando_settings['wepMtMin']
                    elif component.value > game.rando_settings['wepMtMax']:
                        component.value = game.rando_settings['wepMtMax']
                    #logging.debug("%s now has %s might", item.name, component.value)
                if game.rando_settings['wepHit'] and component.nid == 'hit':
                    variance = static_random.get_randint(-game.rando_settings['wepHitVar'],game.rando_settings['wepHitVar'])
                    component.value += variance
                    if component.value < game.rando_settings['wepHitMin']:
                        component.value = game.rando_settings['wepHitMin']
                    elif component.value > game.rando_settings['wepHitMax']:
                        component.value = game.rando_settings['wepHitMax']
                    #logging.debug("%s now has %s hit", item.name, component.value)
                if game.rando_settings['wepCrit'] and component.nid == 'crit':
                    variance = static_random.get_randint(-game.rando_settings['wepCritVar'],game.rando_settings['wepCritVar'])
                    component.value += variance
                    if component.value < game.rando_settings['wepCritMin']:
                        component.value = game.rando_settings['wepCritMin']
                    elif component.value > game.rando_settings['wepCritMax']:
                        component.value = game.rando_settings['wepCritMax']
                    #logging.debug("%s now has %s crit", item.name, component.value)
                if game.rando_settings['wepWeight'] and component.nid == 'weight':
                    variance = static_random.get_randint(-game.rando_settings['wepWeightVar'],game.rando_settings['wepWeightVar'])
                    component.value += variance
                    if component.value < game.rando_settings['wepWeightMin']:
                        component.value = game.rando_settings['wepWeightMin']
                    elif component.value > game.rando_settings['wepWeightMax']:
                        component.value = game.rando_settings['wepWeightMax']
                    #logging.debug("%s now has %s weight", item.name, component.value)
                if game.rando_settings['wepUses'] and component.nid == 'uses':
                    variance = static_random.get_randint(-game.rando_settings['wepUsesVar'],game.rando_settings['wepUsesVar'])
                    component.value += variance
                    if component.value < game.rando_settings['wepUsesMin']:
                        component.value = game.rando_settings['wepUsesMin']
                    elif component.value > game.rando_settings['wepUsesMax']:
                        component.value = game.rando_settings['wepUsesMax']
                    #logging.debug("%s now has %s uses", item.name, component.value)
                if game.rando_settings['wepCUses'] and component.nid == 'c_uses':
                    variance = static_random.get_randint(-game.rando_settings['wepCUsesVar'],game.rando_settings['wepCUsesVar'])
                    component.value += variance
                    if component.value < game.rando_settings['wepCUsesMin']:
                        component.value = game.rando_settings['wepCUsesMin']
                    elif component.value > game.rando_settings['wepCUsesMax']:
                        component.value = game.rando_settings['wepCUsesMax']
                    #logging.debug("%s now has %s c_uses", item.name, component.value)
            #Randomization of weapon effects. Currently for weapons only.
            if game.rando_settings['random_effects'] and any(component.nid == 'weapon' for component in item.components):
                #If we have safe weapons, leave them alone
                if game.rando_settings['safe_basic_weapons'] and item.nid in safe_weapons:
                    continue
                else:
                    #Determine how many effects to place on the weapon. 0 is a valid number
                    amount = static_random.get_randint(0, effect_limit)
                    #If we rolled new effects, remove the old ones if the setting is enabled.
                    if amount > 0 and mode == 'Replace':
                        for component in item.components:
                            if component.nid in specialComponents:
                                item.components.remove_key(component.nid)
                                logging.debug("%s has lost: %s", item.name, component.nid)
                    #Place effects onto weapon
                    for _ in range(amount):
                        selectInt = static_random.get_randint(0, len(validComponents) - 1)
                        effect_to_add = validComponents[selectInt]
                        status_to_add = None
                        if effect_to_add in ['status_on_equip','status_on_hold']:
                            statusInt = static_random.get_randint(0, len(equipSkills) - 1)
                            status_to_add = equipSkills[statusInt]
                            klassName = getClassName('weapon', effect_to_add)
                            effectObj = klassName()
                            effectObj.value = status_to_add
                            item.components.append(effectObj)
                        elif effect_to_add in ['status_on_hit']:
                            statusInt = static_random.get_randint(0, len(statusSkills) - 1)
                            status_to_add = statusSkills[statusInt]
                            klassName = getClassName('hit', effect_to_add)
                            effectObj = klassName()
                            effectObj.value = status_to_add
                            item.components.append(effectObj)
                        #Effective is a bit tricky, since it actually encompasses 2 components
                        elif effect_to_add in ['effective']:
                            if any(component.nid == effect_to_add for component in item.components):
                                compObj = next((component for component in item.components if component.nid == 'effective_tag'), None)
                                existing_tags = compObj.value
                                retry_count = 5
                                for _ in range(retry_count):
                                    tagInt = static_random.get_randint(0, len(effectiveTags) - 1)
                                    newTag = effectiveTags[tagInt]
                                    if not newTag in existing_tags:
                                        compObj.value.append(newTag)
                                        status_to_add = newTag
                                        break
                            else:
                                klassName = getClassName('weapon', effect_to_add)
                                klassName2 = getClassName('weapon', 'effective_tag')
                                effectObj = klassName()
                                effectObj2 = klassName2()
                                item.components.append(effectObj)
                                item.components.append(effectObj2)
                                tagInt = static_random.get_randint(0, len(effectiveTags) - 1)
                                newTag = effectiveTags[tagInt]
                                effectObj2.value = [newTag]
                                status_to_add = newTag
                            if status_to_add:
                                effectObj = next((component for component in item.components if component.nid == 'effective'), None)
                                damageVal = next((component.value for component in item.components if component.nid == 'damage'), None)
                                effectObj.value = damageVal * 2
                        #Some of these could be expanded on. For example, randomized lifelink strength.
                        elif effect_to_add in ['brave','reaver','cannot_counter','cannot_be_countered','magic','lifelink']:
                            klassName = getClassName('weapon', effect_to_add)
                            effectObj = klassName()
                            item.components.append(effectObj)
                        else:
                            pass
                        logging.debug("%s now has new property: %s (%s)", item.name, effect_to_add, status_to_add)
    return newDic

# === Unit Randomization ===
def randomizeNames(game):
    unitDB = game.rando_settings['unitDictionary']
    units_to_rando = []
    names_to_use = []

    #Get units into a dictionary. This will be called by unit.py to alter a unit during runtime.
    for unit in unitDB.values():
        if not 'no_random' in unit.tags:
            units_to_rando.append(unit)
            names_to_use.append(unit.name)

    #Randomize defined unit classes
    while len(units_to_rando) > 0:
        int1 = static_random.get_randint(0, len(units_to_rando) - 1)
        unit_to_pick = units_to_rando[int1]
        int2 = static_random.get_randint(0, len(names_to_use) - 1)
        newName = names_to_use[int2]
        unitDB[unit_to_pick.nid].name = newName

        #We're done with this unit, so remove them from the pool
        logging.debug("%s's new name is: %s", unit_to_pick.name, newName)
        units_to_rando.remove(unit_to_pick)
        names_to_use.remove(newName)

def randomizePortraits(game):
    unitDB = game.rando_settings['unitDictionary']
    units_to_rando = []
    faces_to_use = []

    #Get units into a dictionary. This will be called by unit.py to alter a unit during runtime.
    for unit in unitDB.values():
        if not 'no_random' in unit.tags:
            units_to_rando.append(unit)
            faces_to_use.append(unit.portrait_nid)

    #Randomize defined unit classes
    while len(units_to_rando) > 0:
        int1 = static_random.get_randint(0, len(units_to_rando) - 1)
        unit_to_pick = units_to_rando[int1]
        int2 = static_random.get_randint(0, len(faces_to_use) - 1)
        newFace = faces_to_use[int2]
        unitDB[unit_to_pick.nid].portrait_nid = newFace

        #We're done with this unit, so remove them from the pool
        logging.debug("%s's new face is: %s", unit_to_pick.name, newFace)
        units_to_rando.remove(unit_to_pick)
        faces_to_use.remove(newFace)

def randomizeDescriptions(game):
    unitDB = game.rando_settings['unitDictionary']
    units_to_rando = []
    bios_to_use = []

    #Get units into a dictionary. This will be called by unit.py to alter a unit during runtime.
    for unit in unitDB.values():
        if not 'no_random' in unit.tags:
            units_to_rando.append(unit)
            bios_to_use.append(unit.desc)

    #Randomize defined unit classes
    while len(units_to_rando) > 0:
        int1 = static_random.get_randint(0, len(units_to_rando) - 1)
        unit_to_pick = units_to_rando[int1]
        int2 = static_random.get_randint(0, len(bios_to_use) - 1)
        newDesc = bios_to_use[int2]
        unitDB[unit_to_pick.nid].desc = newDesc

        #We're done with this unit, so remove them from the pool
        logging.debug("%s's new desc is: %s", unit_to_pick.name, newDesc)
        units_to_rando.remove(unit_to_pick)
        bios_to_use.remove(newDesc)

#This is currently unused and unfinished. Will not be looked at again until rainlash determines how he wants to handle personal skills in the engine.
def randomizePersonalSkills(game):
    unitDB = game.rando_settings['unitDictionary']
    units_to_rando = []
    allowed_skills = []
    personal_skill_mode = game.rando_settings['personal_skill_mode']
    amount_limit = game.rando_settings['personal_skill_limit']
    skills_tracker = []
    for skill in DB.skills:
        can_use = True
        for component in skill.components:
            if component.nid in ['hidden','time','negative']:
                can_use = False
                break
        if can_use:
            allowed_skills.append(skill)
    #allowed_skills = [skill for skill in DB.skills if not (any(component.nid == 'Hidden',component.nid == 'time',component.nid == 'negative') for component in skill.components)]
    logging.debug("Skill list: %s", [skill.nid for skill in allowed_skills])

    #If we don't want to repeat personal skills, create a copy of the skills list to track what we've used
    if game.rando_settings['personal_skill_stop_redundancy']:
        skills_tracker = copy.deepcopy(allowed_skills)

    #Figure out who's allowed to have skills randomized
    for unit in unitDB.values():
        if not 'no_random' in unit.tags:
            units_to_rando.append(unit)

    while len(units_to_rando) > 0:
        new_skills = []
        int1 = static_random.get_randint(0, len(units_to_rando) - 1)
        unit_to_pick = units_to_rando[int1]

        #Which skill pool to use
        if 'Player' in unit_to_pick.tags and game.rando_settings['personal_skill_stop_redundancy']:
            list_to_use = skills_tracker
        else:
            list_to_use = allowed_skills

        #Determine how many skills the unit will get
        if personal_skill_mode == 'Match':
            skill_amount = min(len(unit_to_pick.learned_skills), amount_limit)
        elif personal_skill_mode == 'Random':
            skill_amount = static_random.get_randint(0, amount_limit)
        else:
            skill_amount = amount_limit  # Static mode

        #This is where skill choice/assignment occurs
        for _ in range(skill_amount):
            #We ran out of skills, refresh the pool
            if len(list_to_use) <= 0:
                skills_tracker = copy.deepcopy(allowed_skills)
                list_to_use = skills_tracker

            int2 = static_random.get_randint(0, len(list_to_use) - 1)
            skill_to_pick = list_to_use[int2]
            new_skills.append(skill_to_pick)

            if 'Player' in unit_to_pick.tags and game.rando_settings['personal_skill_stop_redundancy']:
                list_to_use.remove(skill_to_pick)

        #Update the unit database and remove this unit from the list, they are done
        unitDB[unit_to_pick.nid].learned_skills = new_skills
        units_to_rando.remove(unit_to_pick)

#Randomizes the skills classes learn, as well as the levels those skills are learned at. Compatible with the other class randos.
def randomizeClassSkills(game):
    klassDB = game.rando_settings['klassDictionary']
    classes_to_rando = []
    allowed_skills = []
    class_skill_mode = game.rando_settings['class_skill_mode']
    amount_limit = game.rando_settings['class_skill_limit']
    skills_tracker = []
    #As a precaution, skills with the components listed below are not eligible to be picked.
    for skill in DB.skills:
        can_use = True
        for component in skill.components:
            if component.nid in ['hidden','time','negative']:
                can_use = False
                break
        if can_use:
            allowed_skills.append(skill.nid)
    #allowed_skills = [skill for skill in DB.skills if not (any(component.nid == 'Hidden',component.nid == 'time',component.nid == 'negative') for component in skill.components)]
    #logging.debug("Skill list: %s", allowed_skills)

    #If we don't want to repeat class skills, create a copy of the skills list to track what we've used
    if game.rando_settings['class_skill_stop_redundancy']:
        skills_tracker = copy.deepcopy(allowed_skills)

    #Figure out which classes are allowed to have skills randomized
    for klass in klassDB:
        if not 'no_random' in klass.tags:
            if (not game.rando_settings['lord_rando'] and 'Lord' in klass.tags) or (not game.rando_settings['thief_rando'] and 'Thief' in klass.tags) or (not game.rando_settings['special_rando'] and 'Special' in klass.tags):
                continue
            else:
                classes_to_rando.append(klass)

    while len(classes_to_rando) > 0:
        new_skills = []
        int1 = static_random.get_randint(0, len(classes_to_rando) - 1)
        class_to_pick = classes_to_rando[int1]
        skill_levels = []

        #Which skill pool to use
        if game.rando_settings['class_skill_stop_redundancy']:
            list_to_use = skills_tracker
        else:
            list_to_use = allowed_skills

        #If we're matching levels with the existing skills, get the levels the skills are learned at
        if game.rando_settings['class_skill_match_levels']:
            for lskill in class_to_pick.learned_skills:
                skill_levels.append(lskill[0])

        #Determine how many skills the class will get
        if class_skill_mode == 'Match':
            skill_amount = min(len(class_to_pick.learned_skills), amount_limit)
        elif class_skill_mode == 'Random':
            skill_amount = static_random.get_randint(0, amount_limit)
        else:
            skill_amount = amount_limit  # Static mode

        #This is where skill choice/assignment occurs
        for _ in range(skill_amount):
            #We ran out of skills, refresh the pool
            if len(list_to_use) <= 0:
                skills_tracker = copy.deepcopy(allowed_skills)
                list_to_use = skills_tracker

            int2 = static_random.get_randint(0, len(list_to_use) - 1)
            skill_to_pick = list_to_use[int2]

            #Determine the learn level
            if game.rando_settings['class_skill_match_levels'] and len(skill_levels) > 0:
                int3 = static_random.get_randint(0, len(skill_levels) - 1)
                level = skill_levels[int3]
                skill_levels.pop(int3)
            else:
                level = static_random.get_randint(0, class_to_pick.max_level)

            newSkill = [level, skill_to_pick]
            new_skills.append(newSkill)

            #Remove from pool if we don't want redundancy (RIP Canto lol)
            if game.rando_settings['class_skill_stop_redundancy']:
                list_to_use.remove(skill_to_pick)

        #Update the class database and remove this class from the list, they are done
        klassDB[class_to_pick.nid].learned_skills = new_skills
        classes_to_rando.remove(class_to_pick)
        logging.debug("New skills for %s: %s", class_to_pick.nid, new_skills)

#For game start
class RandoSettings():
    def __init__(self):
        self.rando_settings = {'class_pools': [],
                               'player_class_rando': False,
                               'player_class_stop_redundancy': False,
                               'lord_rando': False,
                               'thief_rando': False,
                               'special_rando': False,
                               'boss_rando': False,
                               'generic_rando': False,
                               'bases_mode': 'Redistribute',
                               'bases_variance': 0,
                               'boss_bases': False,
                               'player_bases': False,
                               'growths_mode': 'Redistribute',
                               'growths_variance': 0,
                               'growths_min': 0,
                               'growths_max': 100,
                               'named_growths': False,
                               'wepMt': False,
                               'wepMtVar': 0,
                               'wepMtMin': 1,
                               'wepMtMax': 25,
                               'wepHit': False,
                               'wepHitVar': 0,
                               'wepHitMin': 50,
                               'wepHitMax': 100,
                               'wepCrit': False,
                               'wepCritVar': 0,
                               'wepCritMin': 0,
                               'wepCritMax': 50,
                               'wepWeight': False,
                               'wepWeightVar': 0,
                               'wepWeightMin': 2,
                               'wepWeightMax': 20,
                               'wepUses': False,
                               'wepUsesVar': 0,
                               'wepUsesMin': 10,
                               'wepUsesMax': 60,
                               'wepCUses': False,
                               'wepCUsesVar': 0,
                               'wepCUsesMin': 1,
                               'wepCUsesMax': 10,
                               'itemDictionary': {},
                               'wexp_mode': 'Similar',
                               'keepWeps': False,
                               'weps_mode': 'Match',
                               'item_rando': False,
                               'promo_rando': False,
                               'promo_rando_stop_redundancy': False,
                               'promotion_amount': 2,
                               'promoDictionary': {},
                               'promotion_mode': 'Match',
                               'name_rando': False,
                               'portrait_rando': False,
                               'desc_rando': False,
                               'unitDictionary': {},
                               'unitDataDictionary': {},
                               'genericDictionary': {level.nid: {} for level in DB.levels.values()},
                               'Randomized': False,
                               'personal_skill_rando': False,
                               'personal_skill_mode': 'Match',
                               'personal_skill_limit': 1,
                               'personal_skill_stop_redundancy': False,
                               'klassDictionary': {},
                               'class_skill_rando': False,
                               'class_skill_mode': 'Match',
                               'class_skill_limit': 1,
                               'class_skill_stop_redundancy': False,
                               'class_skill_match_levels': False,
                               'random_effects': False,
                               'safe_basic_weapons': False,
                               'random_effects_mode': 'Add',
                               'random_effects_limit': 0,
                               'weapon_properties': [],
                               'weapon_effective': [],
                               'weapon_imbue': [],
                               'weapon_inflict': [],
                               }
def resetRando():
    return {'class_pools': [],
                           'player_class_rando': False,
                           'player_class_stop_redundancy': False,
                           'lord_rando': False,
                           'thief_rando': False,
                           'special_rando': False,
                           'boss_rando': False,
                           'generic_rando': False,
                           'bases_mode': 'Redistribute',
                           'bases_variance': 0,
                           'boss_bases': False,
                           'player_bases': False,
                           'growths_mode': 'Redistribute',
                           'growths_variance': 0,
                           'growths_min': 0,
                           'growths_max': 100,
                           'named_growths': False,
                           'wepMt': False,
                           'wepMtVar': 0,
                           'wepMtMin': 1,
                           'wepMtMax': 25,
                           'wepHit': False,
                           'wepHitVar': 0,
                           'wepHitMin': 50,
                           'wepHitMax': 100,
                           'wepCrit': False,
                           'wepCritVar': 0,
                           'wepCritMin': 0,
                           'wepCritMax': 50,
                           'wepWeight': False,
                           'wepWeightVar': 0,
                           'wepWeightMin': 2,
                           'wepWeightMax': 20,
                           'wepUses': False,
                           'wepUsesVar': 0,
                           'wepUsesMin': 10,
                           'wepUsesMax': 60,
                           'wepCUses': False,
                           'wepCUsesVar': 0,
                           'wepCUsesMin': 1,
                           'wepCUsesMax': 10,
                           'itemDictionary': {},
                           'wexp_mode': 'Similar',
                           'keepWeps': False,
                           'weps_mode': 'Match',
                           'item_rando': False,
                           'promo_rando': False,
                           'promo_rando_stop_redundancy': False,
                           'promotion_amount': 2,
                           'promoDictionary': {},
                           'promotion_mode': 'Match',
                           'name_rando': False,
                           'portrait_rando': False,
                           'desc_rando': False,
                           'unitDictionary': {},
                           'unitDataDictionary': {},
                           'genericDictionary': {level.nid: {} for level in DB.levels.values()},
                           'Randomized': False,
                           'personal_skill_rando': False,
                           'personal_skill_mode': 'Match',
                           'personal_skill_limit': 1,
                           'personal_skill_stop_redundancy': False,
                           'klassDictionary': {},
                           'class_skill_rando': False,
                           'class_skill_mode': 'Match',
                           'class_skill_limit': 1,
                           'class_skill_stop_redundancy': False,
                           'class_skill_match_levels': False,
                           'random_effects': False,
                           'safe_basic_weapons': False,
                           'random_effects_mode': 'Add',
                           'random_effects_limit': 0,
                           'weapon_properties': [],
                           'weapon_effective': [],
                           'weapon_imbue': [],
                           'weapon_inflict': [],
                           }

Rando = RandoSettings()

#Needed for weapon rando, we need a fake unit object to use some item functions to check if stuff is equippable
class SpoofUnit():
    def __init__(self, data, db = None, generic = None):
        self.nid = data.nid
        self.name = data.name
        self.klass = data.klass
        self.level = data.level
        self.items = data.starting_items
        self.skills = []
        if generic:
            klassObj = db.get(self.klass)
            self.tags = klassObj.tags
        else:
            self.tags = data.tags
        #weapon_gain = data.wexp_gain
        #self.wexp = {weapon_nid: weapon_gain.get(weapon_nid, DB.weapons.default()).wexp_gain for weapon_nid in DB.weapons.keys()}

#Mostly to simplify how these are tracked per unit
class UnitData():
    def __init__(self):
        self.wexp = {}
        self.bases = {}
        self.growths = {}

#This is used to help create item components for weapon effects randomization. If custom components are to be added to weapons, a dev may need to edit this method.
def getClassName(type, name):
    if type == 'hit':
        module = importlib.import_module('app.engine.item_components.hit_components')
    else:
        module = importlib.import_module('app.engine.item_components.weapon_components')

    newName = name.replace('_',' ')
    newName = newName.title()
    newName = newName.replace(' ', '')
    klass = getattr(module, newName)
    return klass
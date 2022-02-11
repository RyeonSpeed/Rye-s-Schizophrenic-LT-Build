import math
from collections import Counter

from PyQt5.QtGui import QImage

from app.editor.tile_editor.autotiles import PaletteData

from app.constants import TILEWIDTH, TILEHEIGHT

def bhattacharyya_coefficient(p: dict, q: dict) -> float:
    domain = p.keys() | q.keys()
    total = 0
    p_sum = sum(p.values())
    q_sum = sum(q.values())
    for x in domain:
        if x in p and x in q:  # Only works if the chosen value can be found in both
            p_prob = p[x] / p_sum
            q_prob = q[x] / q_sum
            total += math.sqrt(p_prob * q_prob)
    return total

def hellinger_distance(p: dict, q: dict) -> float:
    """
    Calculates the Hellinger distance of two discrete probability distributions.
    Distance values range from 0 to 1.
    """
    bc = min(bhattacharyya_coefficient(p, q), 1)
    return math.sqrt(1 - bc)

def simple_distance(p: dict, q: dict) -> float:
    """
    Calculates a simple distance between the two discrete probability distributions.
    Just determines the fraction of elements that are shared between the probability distributions.
    Distance values range from 0 to 1.
    """
    shared = len(p.keys() & q.keys())
    p_shared = shared / len(p.keys())
    q_shared = shared / len(q.keys())
    return 1 - max(p_shared, q_shared)

class QuadPaletteData():
    def __init__(self, im: QImage):
        topleft_rect = (0, 0, TILEWIDTH//2, TILEHEIGHT//2)
        self.topleft = PaletteData(im.copy(*topleft_rect))
        topright_rect = (TILEWIDTH//2, 0, TILEWIDTH//2, TILEHEIGHT//2)
        self.topright = PaletteData(im.copy(*topright_rect))
        bottomleft_rect = (0, TILEHEIGHT//2, TILEWIDTH//2, TILEHEIGHT//2)
        self.bottomleft = PaletteData(im.copy(*bottomleft_rect))
        bottomright_rect = (TILEWIDTH//2, TILEHEIGHT//2, TILEWIDTH//2, TILEHEIGHT//2)
        self.bottomright = PaletteData(im.copy(*bottomright_rect))

class MountainQuadPaletteData(QuadPaletteData):
    def __init__(self, im: QImage, coord: tuple):
        super().__init__(im)
        self.coord = coord
        self.rules = {}
        self.rules['left'] = Counter()
        self.rules['right'] = Counter()
        self.rules['up'] = Counter()
        self.rules['down'] = Counter()

def similar(p1: QuadPaletteData, p2: MountainQuadPaletteData, must_match=4) -> bool:

    def similar_fast(p1: list, p2: list) -> int:
        """
        Attempts to compare the pattern of the tiles, not the actual values themselves
        """
        mapping_to = {}
        mapping_fro = {}
        for i, j in zip(p1, p2):
            if i == j:
                mapping_to[i] = j
                mapping_fro[j] = i
            elif (i in mapping_to and j != mapping_to[i]) or (j in mapping_fro and i != mapping_fro[j]):
                return TILEWIDTH * TILEHEIGHT
            else:
                mapping_to[i] = j
                mapping_fro[j] = i
        return 0

    topleft_similar = similar_fast(p1.topleft.palette, p2.topleft.palette) == 0
    topright_similar = similar_fast(p1.topright.palette, p2.topright.palette) == 0
    bottomleft_similar = similar_fast(p1.bottomleft.palette, p2.bottomleft.palette) == 0
    bottomright_similar = similar_fast(p1.bottomright.palette, p2.bottomright.palette) == 0
    num_match = sum((topleft_similar, topright_similar, bottomleft_similar, bottomright_similar))
    return num_match >= must_match

class TileCluster:
    def __init__(self, nid):
        self.nid = nid
        self.coords = set()
        self.secondary_rules = {}
        self.primary_rules = {}
        self.primary_rules['left'] = Counter()
        self.primary_rules['right'] = Counter()
        self.primary_rules['up'] = Counter()
        self.primary_rules['down'] = Counter()

    def save(self):
        s_dict = {}
        s_dict['nid'] = self.nid
        s_dict['secondary_rules'] = self.secondary_rules
        s_dict['primary_rules'] = self.primary_rules

def get_mountain_coords(fn) -> set:
    if fn.endswith('main.png'):
        topleft = {(0, 11), (0, 12), (1, 11), (1, 12), (1, 12), (2, 12), (3, 11), (3, 12)}
        main = {(x, y) for x in range(17) for y in range(13, 20)}
        # (18, 18) is a duplicate of (15, 17)
        right = {(17, 14), (17, 15), (17, 16), (17, 17), (17, 18), (17, 19), (18, 16), (18, 17), (18, 19)}
        bottomleft = {(4, 22), (5, 22), (0, 26), (0, 27), (0, 28), (1, 26), (1, 27), (2, 27), (3, 27)}
        bottom = {(x, y) for x in range(6, 12) for y in range(20, 25)}
        bottomright = {(12, 22), (13, 22), (14, 22), (15, 22), (12, 23), (13, 23), (14, 23), (15, 23), (16, 23), (12, 24), (13, 24), (13, 25), (15, 20), (16, 20), (17, 20), (18, 20), (17, 21), (18, 21)}
        # extra = {(0, 6), (1, 6), (2, 6)}
        extra = {(0, 5), (14, 21)}
        return topleft | main | right | bottomleft | bottom | bottomright | extra
    return set()

def load_mountain_palettes(fn, coords) -> dict:
    palettes = {}
    image = QImage(fn)
    for coord in coords:
        rect = (coord[0] * TILEWIDTH, coord[1] * TILEHEIGHT, TILEWIDTH, TILEHEIGHT)
        palette = image.copy(*rect)
        d = MountainQuadPaletteData(palette, coord)
        palettes[coord] = d
    return palettes

def assign_rules(palette_templates: dict, fns: list):
    print("Assign Rules")
    for fn in fns:
        print("Processing %s..." % fn)
        image = QImage(fn)
        num_tiles_x = image.width() // TILEWIDTH
        num_tiles_y = image.height() // TILEHEIGHT
        image_palette_data = {}
        for x in range(num_tiles_x):
            for y in range(num_tiles_y):
                rect = (x * TILEWIDTH, y * TILEHEIGHT, TILEWIDTH, TILEHEIGHT)
                palette = image.copy(*rect)
                d = QuadPaletteData(palette)
                image_palette_data[(x, y)] = d
        
        best_matches = {} # Position: Mountain Template match
        for position, palette in image_palette_data.items():
            mountain_match = is_present(palette, palette_templates)
            if mountain_match:
                best_matches[position] = mountain_match
        # print({k: v.coord for k, v in best_matches.items()})

        for position, mountain_match in best_matches.items():
            # Find adjacent positions
            left = position[0] - 1, position[1]
            right = position[0] + 1, position[1]
            up = position[0], position[1] - 1
            down = position[0], position[1] + 1
            left_palette = best_matches.get(left)
            right_palette = best_matches.get(right)
            up_palette = best_matches.get(up)
            down_palette = best_matches.get(down)
            # determine if those positions are in palette_templates
            # If they are, mark those coordinates in the list of valid coords
            # If not, mark as end validity
            if left[0] >= 0:
                if left_palette:
                    mountain_match.rules['left'][left_palette.coord] += 1
                else:
                    mountain_match.rules['left'][None] += 1
                    if mountain_match.coord in ((11, 16), (11, 18), (13, 16)):
                        print(fn, position, 'left', mountain_match.coord)
            if right[0] < num_tiles_x:
                if right_palette:
                    mountain_match.rules['right'][right_palette.coord] += 1
                else:
                    mountain_match.rules['right'][None] += 1
                    if mountain_match.coord in ((11, 23), (12, 15)):
                        print(fn, position, 'right', mountain_match.coord)
            if up[1] >= 0:
                if up_palette:
                    mountain_match.rules['up'][up_palette.coord] += 1
                else:
                    mountain_match.rules['up'][None] += 1
                    # if mountain_match.coord in ((2, 12), (1, 16), (1, 17), (4, 18), (8, 19), (9, 19)):
                    #     print(fn, position, 'up', mountain_match.coord)
            if down[1] < num_tiles_y:
                if down_palette:
                    mountain_match.rules['down'][down_palette.coord] += 1
                else:
                    mountain_match.rules['down'][None] += 1
                    if mountain_match.coord in ((13, 16), (17, 15)):
                        print(fn, position, 'down', mountain_match.coord)

def is_present(palette: QuadPaletteData, palette_templates: dict) -> MountainQuadPaletteData:
    MUST_MATCH = 4
    for coord, mountain in palette_templates.items():
        if similar(palette, mountain, MUST_MATCH):
            return mountain
    return None

def calc_distance(palette1, palette2) -> float:
    directions = ('left', 'right', 'up', 'down')
    return max([hellinger_distance(palette1.rules[direction], palette2.rules[direction]) for direction in directions])

def get_closest_clusters(mountain_palettes: dict, clusters: list) -> tuple:
    min_distance: float = 1
    min_cluster1: TileCluster, min_cluster2: TileCluster = None, None
    for cluster1, cluster2 in itertools.combinations(clusters, 2):
        max_distance: float = 0
        for coord1 in cluster1.coords:
            for coord2 in cluster2.coords:
                dist = calc_distance(mountain_palettes[coord1], mountain_palettes[coord2])
                if dist > max_distance:
                    max_distance = dist
        if max_distance < min_distance:
            min_distance = max_distance
            min_cluster1 = cluster1
            min_cluster2 = cluster2
    # Rearrange order if necessary
    if min_cluster1.nid > min_cluster2.nid:
        min_cluster1, min_cluster2 = min_cluster2, min_cluster1  # swap
    return min_cluster1, min_cluster2, min_distance

def generate_clusters(mountain_palettes: dict):
    """
    Attempts to simplify the ~195 tiles by clustering similar ones together
    This should speed up the mountain generation in later steps
    """
    directions = ('left', 'right', 'up', 'down')
    # create initial clusters
    clusters = []
    for coord in mountain_palettes.keys():
        new_cluster = TileCluster(len(clusters))
        new_cluster.coords.add(coord)
        clusters.append(new_cluster)

    # Now repeatedly determine which cluster are closest, and combine them
    while True:
        cluster1, cluster2, distance = get_closest_clusters(mountain_palettes, clusters)
        cluster1.coords |= cluster2.coords
        clusters.remove(cluster2)
        if distance > 0.5:
            break

    print("--- Clusters ---")
    for cluster in clusters:
        print(cluster.nid, len(cluster.coords), cluster.coords)
    # Now populate clusters with their individual rules
    for cluster in clusters:
        for coord in cluster.coords:
            palette = mountain_palettes[coord]
            cluster.secondary_rules[coord] = palette.rules
    # Now connect clusters with one another using the final rules
    for cluster in clusters:
        for coord, rules in cluster.secondary_rules.items():
            for direction in directions:
                for other_coord, incidence in rules[direction].items():
                    for other_cluster in clusters:
                        if other_coord in other_cluster.coords:
                            cluster.primary_rules[direction][other_cluster.nid] += incidence
                            break
    # Should now be connected
    for cluster in clusters:
        for direction in directions:
            print(cluster.nid, direction, cluster.primary_rules[direction])
    return clusters

if __name__ == '__main__':
    import os, sys, glob
    try:
        import cPickle as pickle
    except ImportError:
        import pickle

    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)

    tileset = 'app/map_maker/palettes/westmarch/main.png'
    mountain_coords = get_mountain_coords(tileset)

    mountain_palettes = load_mountain_palettes(tileset, mountain_coords)
    home_dir = os.path.expanduser('~')
    mountain_data_dir = glob.glob(home_dir + '/Pictures/Fire Emblem/MapReferences/custom_mountain_data/*.png')
    # Stores rules in the palette data itself
    assign_rules(mountain_palettes, mountain_data_dir)
    # Generates clusters
    clusters = generate_clusters(mountain_palettes)

    save_data = [c.save() for c in clusters]

    # print("--- Final Rules ---")
    # final_rules = {coord: mountain_palette.rules for coord, mountain_palette in mountain_palettes.items()}
    # to_watch = []
    # for coord, rules in sorted(final_rules.items()):
    #     print("---", coord, "---")
    #     if rules['left']:
    #         print('left', rules['left'])
    #     if rules['right']:
    #         print('right', rules['right'])
    #     if rules['up']:
    #         print('up', rules['up'])
    #     if rules['down']:
    #         print('down', rules['down'])
    #     if None in rules['left'] and rules['left'][None] < (0.1 * sum(rules['left'].values())):
    #         to_watch.append((coord, 'left'))
    #     if None in rules['right'] and rules['right'][None] < (0.1 * sum(rules['right'].values())):
    #         to_watch.append((coord, 'right'))
    #     if None in rules['up'] and rules['up'][None] < (0.1 * sum(rules['up'].values())):
    #         to_watch.append((coord, 'up'))
    #     if None in rules['down'] and rules['down'][None] < (0.1 * sum(rules['down'].values())):
    #         to_watch.append((coord, 'down'))
    # print("--- Watch for: ---")
    # print(to_watch)

    data_loc = 'app/map_maker/mountain_data.p'
    with open(data_loc, 'wb') as fp:
        pickle.dump(save_data, fp)

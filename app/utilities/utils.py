import math
from collections import Counter
import colorsys, hashlib

class Multiset(Counter):
    def __contains__(self, item):
        return self[item] > 0

def clamp(i, min_, max_):
    return min(max_, max(min_, i))

def sign(n):
    return 1 if n >= 0 else -1

def lerp(a, b, t):
    t = clamp(t, 0, 1)
    return (b - a) * t + a

def distance(pos1, pos2):
    """
    Euclidean distance
    """
    return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)

def model_wave(time, period, width) -> float:
    """
    Models a rise time of width/2 followed immediately by a fall time of width/2
    Each wave is separated by (period - width) milliseconds
    """
    cur_time = time % period
    half_width = width//2
    if cur_time < half_width:
        return float(cur_time) / half_width
    elif cur_time < width:
        return 1 - float(cur_time - half_width) / half_width
    else:
        return 0

def compare_teams(t1: str, t2: str) -> bool:
    # Returns True if allies, False if enemies
    if t1 is None or t2 is None:
        return None
    elif t1 == t2:
        return True
    elif (t1 == 'player' and t2 == 'other') or (t2 == 'player' and t1 == 'other'):
        return True
    else:
        return False

def get_team_color(team: str):
    team_dict = {'player': 'blue',
                 'enemy': 'red',
                 'other': 'green',
                 'enemy2': 'purple'}
    return team_dict.get(team, 'red')

def calculate_distance(pos1: tuple, pos2: tuple) -> int:
    """
    Taxicab/Manhattan distance
    """
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

def process_terms(terms):
    """ 
    Processes weighted lists
    """
    weight_sum = sum(term[1] for term in terms)
    if weight_sum <= 0:
        return 0
    return sum(float(val * weight) for weight, val in terms) / weight_sum

def dot_product(a: tuple, b: tuple) -> float:
    return sum(a[i] * b[i] for i in range(len(b)))

def strhash(s: str) -> int:
    """
    Converts a string to a corresponding integer
    """
    h = hashlib.md5(s.encode('utf-8'))
    h = int(h.hexdigest(), base=16)
    return h

def hash_to_color(h: int) -> tuple:
    hue = h % 359
    saturation_array = lightness_array = [0.35, 0.5, 0.65]
    saturation = saturation_array[h // 360 % len(saturation_array)]
    idx = int(h * saturation // 360 % len(lightness_array))
    lightness = lightness_array[idx]
    color = colorsys.hls_to_rgb(hue / 360., lightness, saturation)
    return tuple([int(_ * 255) for _ in color])

def average_pos(pos_list: list) -> tuple:
    avg_x, avg_y = 0, 0
    for x, y in pos_list:
        avg_x += x
        avg_y += y
    avg_x /= len(pos_list)
    avg_y /= len(pos_list)
    return (avg_x, avg_y)

def farthest_away_pos(pos: tuple, valid_moves: set, enemy_pos: set):
    if valid_moves and enemy_pos:
        avg_pos = average_pos(enemy_pos)
        # First furthest away point from avg_pos
        # Then closest point to current position
        return sorted(valid_moves, key=lambda move: (calculate_distance(avg_pos, move), -calculate_distance(pos, move)))[-1]
    else:
        return None

def smart_farthest_away_pos(position, valid_moves: set, enemy_pos: set):
    # Figure out avg position of enemies
    if valid_moves and enemy_pos:
        avg_x, avg_y = 0, 0
        for pos, mag in enemy_pos:
            diff_x = position[0] - pos[0]
            diff_y = position[1] - pos[1]
            diff_x /= mag
            diff_y /= mag
            avg_x += diff_x
            avg_y += diff_y
        avg_x /= len(enemy_pos)
        avg_y /= len(enemy_pos)
        # Now have vector pointing away from average enemy position
        # I want the dot product between that vector and the vector of each possible move
        # The highest dot product is the best 
        return sorted(valid_moves, key=lambda move: dot_product((move[0] - position[0], move[1] - position[1]), (avg_x, avg_y)))[-1]
    else:
        return None

def raytrace(pos1: tuple, pos2: tuple) -> list:
    """
    Draws line between pos1 and pos2 for a taxicab grid
    """
    x0, y0 = pos1
    x1, y1 = pos2
    tiles = []
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    x, y = x0, y0
    n = 1 + dx + dy
    x_inc = 1 if x1 > x0 else -1
    y_inc = 1 if y1 > y0 else -1
    error = dx - dy
    dx *= 2
    dy *= 2

    while n > 0:
        tiles.append((x, y))
        if error > 0:
            x += x_inc
            error -= dy
        else:
            y += y_inc
            error += dx
        n -= 1
    return tiles

# Testing
if __name__ == '__main__':
    c = Counter()
    # import time
    # orig_time = time.time_ns()
    with open('../../../english_corpus.txt') as corpus:
        for line in corpus:
            i = strhash(line)
            b = i % 359
            c[b] += 1
    for n in range(1000000):
        i = strhash(str(n))
        b = i % 359
        c[b] += 1
    # print((time.time_ns() - orig_time)/1e6)
    print(sorted(c.items()))

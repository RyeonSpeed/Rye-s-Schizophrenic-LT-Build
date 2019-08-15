from app.data.database import DB

class TileMap(object):
    def __init__(self, image_fn, terrain_fn):
        map_key, self.width, self.height = self.build_map_key(terrain_fn)

        self.tiles = {} # The mechanical information about the tile organized by position
        self.tile_sprites = {}  # The sprite information about the tile organized by position

        self.populate_tiles(map_key)
        self.base_image = image_fn

    def build_map_key(self, terrain_fn):
        with open(terrain_fn) as fp:
            lines = [l.strip().split() for l in fp.readlines()]
        width = len(lines[0])
        height = len(lines)

        return lines, width, height

    def populate_tiles(self, map_key):
        for x in range(self.width):
            for y in range(self.height):
                terrain = DB.terrain.get(int(map_key[y][x]))
                new_tile = Tile(terrain, (x, y), self)
                self.tiles[(x, y)] = new_tile

    @classmethod
    def default(cls):
        return cls("./app/data/default_tilemap_image.png", "./app/data/default_tilemap_terrain.txt")

class Tile(object):
    def __init__(self, terrain, position, parent):
        self.parent = parent
        self.terrain = terrain
        self.position = position

        self.current_hp = 0

class TileSprite(object):
    def __init__(self, image, position, parent):
        self.image = image
        self.parent = parent
        self.position = position

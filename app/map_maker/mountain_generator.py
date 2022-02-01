try:
    import cPickle as pickle
except ImportError:
    import pickle

from app.map_maker.utilities import random_choice, find_bounding_rect
class Generator():
    MAX_SIZE = 3
    NUM_VARIANTS = 10

    def __init__(self):
        self.seed = 0
        self.organization = {}
        self.to_process = []  # Keeps track of what tiles still need to be process for group
        self.order = []  # Keeps track of the order that tiles have been processed
        self.locked_values = {}  # Keeps track of what coords unfortunately don't work
        self.mountain_data = None

        self.terrain_grid = None
        # self.terrain_grids = self.generate_terrain_grids()
        self.terrain_grids = self.generate_simple_terrain_grid()

        data_loc = 'app/map_maker/mountain_data.p'
        with open(data_loc, 'rb') as fp:
            self.mountain_data = pickle.load(fp)
        self.border_dict = {}  # Coord: Index (0-15)
        self.index_dict = {i: set() for i in range(16)}  # Index: Coord 
        for coord, rules in self.mountain_data.items():
            north_edge = None in rules['up']
            south_edge = None in rules['down']
            east_edge = None in rules['right']
            west_edge = None in rules['left']
            index = 1 * north_edge + 2 * east_edge + 4 * south_edge + 8 * west_edge
            self.border_dict[coord] = index
            self.index_dict[index].add(coord)
        for index, coord in self.index_dict.items():
            print(index, sorted(coord))

        import time
        total_time = 0
        self.terrain_organization = {}
        for terrain_grid in self.terrain_grids:
            print(terrain_grid)
            self.terrain_grid = terrain_grid
            if self.terrain_grid not in self.terrain_organization:
                self.terrain_organization[self.terrain_grid] = []
            # For each seed
            start = time.time_ns() / 1e6
            for idx in range(self.NUM_VARIANTS):
                print(idx)
                self.seed = idx
                self.organization.clear()
                self.process_terrain_grid()
                self.terrain_organization[self.terrain_grid].append(self.organization.copy())
            duration = time.time_ns() / 1e6 - start
            print(duration)
            total_time += duration
        print("Total Time %f ms" % total_time)

    def flood_fill(self, pos: tuple) -> set:
        blob_positions = set()
        unexplored_stack = []

        def find_similar(starting_pos: tuple):
            unexplored_stack.append(starting_pos)

            counter = 0
            while unexplored_stack and counter < 99999:
                current_pos = unexplored_stack.pop()

                if current_pos in blob_positions:
                    continue
                if not self.get_terrain(current_pos):
                    continue

                blob_positions.add(current_pos)
                unexplored_stack.append((current_pos[0] + 1, current_pos[1]))
                unexplored_stack.append((current_pos[0] - 1, current_pos[1]))
                unexplored_stack.append((current_pos[0], current_pos[1] + 1))
                unexplored_stack.append((current_pos[0], current_pos[1] - 1))
                counter += 1
            if counter >= 99999:
                raise RuntimeError("Unexpected infinite loop in generic flood_fill")

        # Determine which coords should be flood-filled
        find_similar(pos)
        return blob_positions

    def generate_terrain_grids_procedural(self) -> list:
        terrain_grids = set()
        size = self.MAX_SIZE
        square = size**2
        for num in range(1, 2**square):
            terrain_grid = set()
            b = bin(num)[2:][-square:]
            b = '0'*(square - len(b)) + b
            for counter in range(square):
                x = counter % size
                y = counter // size
                if b[counter] == '1':
                    terrain_grid.add((x, y))
            x_start, y_start, width, height = find_bounding_rect(terrain_grid)
            self.terrain_grid = {(pos[0] - x_start, pos[1] - y_start) for pos in terrain_grid}
            # Check if it's fully contiguous
            near_positions: set = self.flood_fill(next(iter(self.terrain_grid)))
            if len(near_positions) == len(self.terrain_grid):
                terrain_grids.add(frozenset(self.terrain_grid))
        return list(terrain_grids)

    def generate_terrain_grids(self) -> list:
        terrain_grids = set()
        terrain_grid_example = {
            (0, 2), (0, 4), (0, 5), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6),
            (2, 2), (2, 3), (2, 4), (2, 5), (2, 6), (2, 7),
            (3, 1), (3, 2), (3, 3), (3, 4), (3, 5), (3, 6), (3, 7),
            (4, 1), (4, 2), (4, 3), (4, 4), (4, 5), (4, 6), (4, 7),
            (5, 0), (5, 1), (5, 2), (5, 3), (5, 4), (5, 5), (5, 6),
            (6, 1), (6, 2), (6, 3), (6, 4), (6, 5), (6, 6),
            (7, 4)
        }
        terrain_grids.add(frozenset(terrain_grid_example))
        return list(terrain_grids)

    def generate_simple_terrain_grid(self) -> list:
        terrain_grids = set()
        terrain_grid_example = {
            (0, 0), (0, 1), (1, 0), (1, 1), (2, 0)
        }
        terrain_grids.add(frozenset(terrain_grid_example))
        return list(terrain_grids)

    def determine_sprite_coords(self, tilemap, pos: tuple) -> tuple:
        new_coords = self.organization[pos]
        new_coords1 = [(new_coords[0]*2, new_coords[1]*2)]
        new_coords2 = [(new_coords[0]*2 + 1, new_coords[1]*2)]
        new_coords3 = [(new_coords[0]*2 + 1, new_coords[1]*2 + 1)]
        new_coords4 = [(new_coords[0]*2, new_coords[1]*2 + 1)]
        return new_coords1, new_coords2, new_coords3, new_coords4

    def find_valid_coord(self, pos) -> bool:
        north, east, south, west = self.get_cardinal_terrain(pos)
        north_edge = not north
        south_edge = not south
        east_edge = not east
        west_edge = not west
        valid_coords = \
            [coord for coord, rules in self.mountain_data.items() if
             ((north_edge and None in rules['up']) or (not north_edge and rules['up'])) and
             ((south_edge and None in rules['down']) or (not south_edge and rules['down'])) and
             ((east_edge and None in rules['right']) or (not east_edge and rules['right'])) and
             ((west_edge and None in rules['left']) or (not west_edge and rules['left']))]
        north_pos = (pos[0], pos[1] - 1)
        south_pos = (pos[0], pos[1] + 1)
        east_pos = (pos[0] + 1, pos[1])
        west_pos = (pos[0] - 1, pos[1])
        # print("*Valid Coord", pos, self.order)
        # print(sorted(valid_coords))
        # Remove locked coords
        if pos in self.locked_values:
            # print("Locked", sorted(self.locked_values[pos]))
            valid_coords = [coord for coord in valid_coords if coord not in self.locked_values[pos]]
        if not north_edge and north_pos in self.organization:
            chosen_coord = self.organization[north_pos]
            valid_coords = [coord for coord in valid_coords if coord in self.mountain_data[chosen_coord]['down']]
        if not south_edge and south_pos in self.organization:
            chosen_coord = self.organization[south_pos]
            valid_coords = [coord for coord in valid_coords if coord in self.mountain_data[chosen_coord]['up']]
        if not east_edge and east_pos in self.organization:
            chosen_coord = self.organization[east_pos]
            valid_coords = [coord for coord in valid_coords if coord in self.mountain_data[chosen_coord]['left']]
        if not west_edge and west_pos in self.organization:
            chosen_coord = self.organization[west_pos]
            valid_coords = [coord for coord in valid_coords if coord in self.mountain_data[chosen_coord]['right']]
        # print(sorted(valid_coords))
        if not valid_coords:
            # print("Reverting Order...")
            if pos in self.locked_values:
                del self.locked_values[pos]
            self.revert_order()
            # valid_coords = self.index_dict[15]
            return False
        valid_coord = random_choice(list(valid_coords), pos, self.seed)
        # print("Final", valid_coord)
        self.organization[pos] = valid_coord
        return True

    def find_valid_coords(self, pos) -> list:
        north, east, south, west = self.get_cardinal_terrain(pos)
        north_edge = not north
        south_edge = not south
        east_edge = not east
        west_edge = not west
        valid_coords = \
            [coord for coord, rules in self.mountain_data.items() if
             ((north_edge and None in rules['up']) or (not north_edge and rules['up'])) and
             ((south_edge and None in rules['down']) or (not south_edge and rules['down'])) and
             ((east_edge and None in rules['right']) or (not east_edge and rules['right'])) and
             ((west_edge and None in rules['left']) or (not west_edge and rules['left']))]
        return valid_coords

    def revert_order(self):
        if not self.order:
            print("Major loop error! No valid solution")
            # Just fill it up with generic pieces
            for pos in self.to_process:
                valid_coords = self.index_dict[15]
                valid_coord = random_choice(list(valid_coords), pos, self.seed)
                self.organization[pos] = valid_coord
            self.to_process.clear()
            return

        pos = self.order.pop()
        coord = self.organization[pos]
        del self.organization[pos]
        self.to_process.insert(0, pos)
        if pos not in self.locked_values:
            self.locked_values[pos] = set()
        self.locked_values[pos].add(coord)
        # print("Locking ", coord, "for ", pos)

    def get_terrain(self, pos: tuple) -> bool:
        return pos in self.terrain_grid

    def get_cardinal_terrain(self, pos: tuple) -> tuple:
        north = self.get_terrain((pos[0], pos[1] - 1))
        east = self.get_terrain((pos[0] + 1, pos[1]))
        south = self.get_terrain((pos[0], pos[1] + 1))
        west = self.get_terrain((pos[0] - 1, pos[1]))
        return north, east, south, west

    def find_num_borders(self, pos) -> int:
        north, east, south, west = self.get_cardinal_terrain(pos)
        num_borders = sum((not north, not south, not east, not west))
        return num_borders

    def find_num_partners(self, pos) -> int:
        north_pos = (pos[0], pos[1] - 1)
        south_pos = (pos[0], pos[1] + 1)
        east_pos = (pos[0] + 1, pos[1])
        west_pos = (pos[0] - 1, pos[1])
        north_edge = north_pos in self.organization
        south_edge = south_pos in self.organization
        east_edge = east_pos in self.organization
        west_edge = west_pos in self.organization
        num_partners = sum((north_edge, south_edge, east_edge, west_edge))
        return num_partners

    def process_terrain_grid_recursive_backtracking(self):
        # Determine coord 
        # print("--- Process Group ---")
        self.locked_values.clear()
        self.order.clear()
        self.to_process = sorted(self.terrain_grid)

        def process(seq):
            pos = seq[0]
            did_work = self.find_valid_coord(pos)
            if did_work:
                self.to_process.remove(pos)
                self.order.append(pos)
            self.to_process = sorted(self.to_process)

        while self.to_process:
            process(self.to_process)

    def process_terrain_grid(self):
        import app.map_maker.dancing_links as dancing_links
        self.to_process = sorted(self.terrain_grid)

        columns = [(pos, dancing_links.DLX.PRIMARY) for pos in self.to_process]
        # valid_coords = [self.find_valid_coords(pos) for pos in self.to_process]
        valid_coords_dict = {pos: self.find_valid_coords(pos) for pos in self.to_process}

        rows = []
        row_names = []

        for idx, pos in enumerate(self.to_process):
            right = (pos[0] + 1, pos[1])
            down = (pos[0], pos[1] + 1)
            for valid_coord in valid_coords_dict[pos]:
                row = [idx]
                rows.append(row)
                row_names.append((pos[0], pos[1], valid_coord[0], valid_coord[1]))

                # Right
                if right in self.to_process:
                    valid_coords_right = [coord for coord in self.mountain_data[valid_coord]['right'] if coord in valid_coords_dict[right]]
                    for possible_partner_coord in valid_coords_right:
                        identifier = (*pos, *right, *valid_coord, *possible_partner_coord)
                        columns.append((identifier, dancing_links.DLX.PRIMARY))
                        row.append()
                # Down
                if down in self.to_process:
                    valid_coords_down = [coord for coord in self.mountain_data[valid_coord]['down'] if coord in valid_coords_dict[down]]
                    for possible_partner_coord in valid_coords_down:
                        identifier = (*pos, *right, *valid_coord, *possible_partner_coord)
                        columns.append((identifier, dancing_links.DLX.PRIMARY))

        print("Columns")
        print([c[0] for c in columns])
        print("Rows")
        print(row_names)

        d = dancing_links.DLX(columns)                
        d.appendRows(rows, row_names)

        sol = d.solve()
        print("Solution:")
        row_names = []
        for i in sol:
            row_names.append(d.N[i])
        print(row_names)
        for x, y, coord_x, coord_y in row_names:
            self.organization[(x, y)] = (coord_x, coord_y)

# Run from main lt-maker directory with
# python -m app.map_maker.mountain_generator
if __name__ == '__main__':
    import os, sys

    from PyQt5.QtGui import QImage, QColor, QPainter
    from PyQt5.QtWidgets import QApplication

    from app.constants import TILEWIDTH, TILEHEIGHT

    app = QApplication(sys.argv)

    tileset = 'app/map_maker/rainlash_fields1.png'
    save_dir = 'app/map_maker/test_output/'
    if not os.path.exists(save_dir):
        os.mkdir(save_dir)
    main_image = QImage(tileset)

    g = Generator()
    for key, terrain_grids in g.terrain_organization.items():
        print(key)
        _, _, width, height = find_bounding_rect(key)

        for idx, terrain_grid in enumerate(terrain_grids):
            new_im = QImage(width * TILEWIDTH, height * TILEHEIGHT, QImage.Format_RGB32)
            new_im.fill(QColor(0, 0, 0))
            painter = QPainter()
            painter.begin(new_im)

            for pos, coord in terrain_grid.items():
                rect = (coord[0] * TILEWIDTH, coord[1] * TILEHEIGHT, TILEWIDTH, TILEHEIGHT)
                im = main_image.copy(*rect)
                painter.drawImage(pos[0] * TILEWIDTH, pos[1] * TILEHEIGHT, im)

            painter.end()

            h = str(hash(key))[:16]
            new_im.save(save_dir + ('%s_%02d.png' % (h, idx)))

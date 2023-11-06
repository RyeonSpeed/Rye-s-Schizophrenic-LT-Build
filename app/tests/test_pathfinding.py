import unittest

from app.engine.grid import BoundedGrid
from app.engine.pathfinding import node, pathfinding

class PathfindingTests(unittest.TestCase):
    """
    Tests all of the pathfinders in the pathfinding module
    """
    def setUp(self):
        # Simple grid
        width, height = 11, 11
        self.simple_grid = BoundedGrid((width, height), (1, 1, 10, 10))
        for x in range(width):
            for y in range(height):
                self.simple_grid.insert((x, y), node.Node((x, y), True, 1))

        # Complex grid
        width, height = 10, 10
        self.complex_grid = BoundedGrid((width, height), (1, 3, 8, 10))
        walls = {(3, 3), (3, 4), (3, 5), (3, 6), (3, 8), (3, 9), (3, 10), (6, 4), 
                 (6, 5), (6, 6), (6, 7), (6, 8), (6, 9), (6, 10)}
        mud = {(2, 6), (2, 7), (2, 8), (3, 7), (4, 6), (4, 7), (4, 8)}
        for x in range(width):
            for y in range(height):
                pos = (x, y)
                cost = 1
                if pos in walls:
                    cost = 99
                elif pos in mud:
                    cost = 2
                self.complex_grid.insert((x, y), node.Node((x, y), cost < 99, cost))

    def test_djikstra(self):
        # Testing the simple grid
        pathfinder = pathfinding.Djikstra((5, 5), self.simple_grid)
        can_move_through = lambda x: True
        valid_moves = pathfinder.process(can_move_through, 5)
        self.assertNotIn((1, 1), valid_moves, 'Moved too far')
        self.assertNotIn((5, 0), valid_moves, 'Ignored bounds')
        self.assertNotIn((0, 5), valid_moves, 'Ignored bounds')
        self.assertIn((1, 1), valid_moves, 'Original position should be a valid move')
        self.assertEqual(len(valid_moves), 57,
                         'Found the incorrect number of moves')

        # Test idempotency
        valid_moves = pathfinder.process(can_move_through, 5)
        self.assertEqual(len(valid_moves), 57,
                         'Djikstra is not idempotent')

        # Test walls, terrain costs
        pathfinder = pathfinding.Djikstra((1, 7), self.complex_grid)
        valid_moves = pathfinder.process(can_move_through, 5)
        self.assertNotIn((0, 7), valid_moves, 'Ignored bounds')
        self.assertNotIn((4, 7), valid_moves, 'Ignored terrain cost')
        self.assertNotIn((3, 6), valid_moves, 'Ignored wall')
        self.assertNotIn((3, 6), valid_moves, 'Ignored wall')

    def test_astar(self):
        # Test the simple grid with no limit
        pathfinder = pathfinding.AStar((5, 5), None, self.simple_grid)
        pathfinder.set_goal_pos((1, 1))
        can_move_through = lambda x: True
        path = pathfinder.process(can_move_through)
        self.assertEqual(path[-1], (1, 1), 'Did not find the end')
        self.assertEqual(path[0], (5, 5), 'Did not start at the beginning')
        self.assertEqual(len(path), 8, 'Longer path than necessary')
        self.assertIn((4, 4), path, 'Did not take diagonal')
        self.assertIn((2, 2), path, 'Did not take diagonal')

        # Test the complex grid with no limit
        pathfinder = pathfinding.AStar((1, 7), (7, 7), self.complex_grid)
        path = pathfinder.process(can_move_through)
        self.assertEqual(path[-1], (7, 7), 'Did not find the end')
        self.assertEqual(path[0], (1, 7), 'Did not start at the beginning')
        self.assertEqual(len(path), 15, f'Longer path than necessary {path}')

        # Test the complex grid with a limit
        path = pathfinder.process(can_move_through, limit=7)
        self.assertEqual(path[-1], (5, 7), 'Did not find the best end')
        self.assertEqual(path[0], (1, 7), 'Did not start at the beginning')

        # Test the complex grid with adj_good_enough
        path = pathfinder.process(can_move_through, adj_good_enough=True)
        self.assertEqual(path[-1], (7, 8), 'Did not find the best end')

    def test_thetastar(self):
        # Test the simple grid
        pathfinder = pathfinding.ThetaStar((5, 5), (1, 1), self.simple_grid)
        can_move_through = lambda x: True
        path = pathfinder.process(can_move_through)
        self.assertEqual(path[-1], (1, 1), 'Did not find the end')
        self.assertEqual(path[0], (5, 5), 'Did not start at the beginning')
        self.assertEqual(len(path), 2, f'Longer path than necessary {path}')

        # Test the complex grid
        pathfinder = pathfinding.ThetaStar((1, 7), (7, 7), self.complex_grid)
        path = pathfinder.process(can_move_through)
        self.assertEqual(path[-1], (7, 7), 'Did not find the end')
        self.assertEqual(path[0], (1, 7), 'Did not start at the beginning')
        self.assertEqual(len(path), 4, f'Longer path than necessary {path}')

if __name__ == '__main__':
    unittest.main()

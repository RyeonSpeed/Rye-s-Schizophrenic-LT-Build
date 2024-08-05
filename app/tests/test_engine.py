import unittest

from app.engine import engine

class EngineTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_subsurface_fix(self):
        # Confirm that we return the same size when everything is good
        main_surf_size = (48, 48)
        subsurface_rect = (10, 10, 10, 10)
        new_rect = engine._subsurface_fix(main_surf_size, subsurface_rect)
        self.assertEqual(subsurface_rect, new_rect)

        # Subsurface is too big on bottomright
        main_surf_size = (48, 48)
        subsurface_rect = (8, 8, 50, 50)
        should_be = (8, 8, 40, 40)
        new_rect = engine._subsurface_fix(main_surf_size, subsurface_rect)
        self.assertEqual(should_be, new_rect)

        # Subsurface is too big just on right
        main_surf_size = (48, 48)
        subsurface_rect = (0, 0, 100, 36)
        should_be = (0, 0, 48, 36)
        new_rect = engine._subsurface_fix(main_surf_size, subsurface_rect)
        self.assertEqual(should_be, new_rect)

        # Subsurface is too big just on bottom
        main_surf_size = (48, 48)
        subsurface_rect = (0, 0, 36, 100)
        should_be = (0, 0, 36, 48)
        new_rect = engine._subsurface_fix(main_surf_size, subsurface_rect)
        self.assertEqual(should_be, new_rect)

        # Subsurface is too big on topleft
        main_surf_size = (48, 48)
        subsurface_rect = (-4, -4, 48, 40)
        should_be = (0, 0, 44, 36)
        new_rect = engine._subsurface_fix(main_surf_size, subsurface_rect)
        self.assertEqual(should_be, new_rect)

        # Subsurface is too big just on left
        main_surf_size = (48, 48)
        subsurface_rect = (-20, 0, 48, 48)
        should_be = (0, 0, 28, 48)
        new_rect = engine._subsurface_fix(main_surf_size, subsurface_rect)
        self.assertEqual(should_be, new_rect)

        # Subsurface is too big just on top
        main_surf_size = (48, 48)
        subsurface_rect = (0, -4, 36, 32)
        should_be = (0, 0, 36, 28)
        new_rect = engine._subsurface_fix(main_surf_size, subsurface_rect)
        self.assertEqual(should_be, new_rect)

        # Subsurface is always too big
        main_surf_size = (48, 48)
        subsurface_rect = (-12, -4, 56, 64)
        should_be = (0, 0, 44, 48)
        new_rect = engine._subsurface_fix(main_surf_size, subsurface_rect)
        self.assertEqual(should_be, new_rect)

        # Subsurface is always too big
        main_surf_size = (48, 48)
        subsurface_rect = (-36, -48, 96, 124)
        should_be = (0, 0, 48, 48)
        new_rect = engine._subsurface_fix(main_surf_size, subsurface_rect)
        self.assertEqual(should_be, new_rect)

        # Subsurface is not even in the main rect
        main_surf_size = (48, 48)
        subsurface_rect = (-36, -32, 12, 8)
        should_be = (0, 0, 1, 1)
        new_rect = engine._subsurface_fix(main_surf_size, subsurface_rect)
        self.assertEqual(should_be, new_rect)

        # Subsurface is not even in the main rect
        main_surf_size = (48, 48)
        subsurface_rect = (56, 64, 8, 8)
        should_be = (47, 47, 1, 1)
        new_rect = engine._subsurface_fix(main_surf_size, subsurface_rect)
        self.assertEqual(should_be, new_rect)

        # surface is really smol
        main_surf_size = (1, 1)
        subsurface_rect = (56, 64, 8, 8)
        should_be = (0, 0, 1, 1)
        new_rect = engine._subsurface_fix(main_surf_size, subsurface_rect)
        self.assertEqual(should_be, new_rect)

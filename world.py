import pygame
import random
import config
from math import sqrt

class Plant:
    def __init__(self, x, y, max_food, nutrient):
        self.x = x
        self.y = y
        self.max_food = max_food
        self.food_count = max_food
        self.nutrient = nutrient
        self.age = 0
        self.dead = False

    def grow(self, multiplier=1.0):
        growth = int(5 * multiplier)
        self.food_count = min(self.max_food, self.food_count + growth)

    def eat(self):
        if self.food_count > 0:
            self.food_count -= 1
            return self.nutrient
        return 0

    def update(self):
        self.age += 1
        if self.age > self.max_age or self.food_count <= 0:
            self.dead = True

class Tree(Plant):
    def __init__(self, x, y):
        super().__init__(x, y, config.TREE_MAX_LEAVES, config.TREE_LEAF_NUTRIENT)
        self.radius = 15
        self.max_age = config.PLANT_MAX_AGE * random.uniform(0.8, 1.2)

class Bush(Plant):
    def __init__(self, x, y):
        super().__init__(x, y, config.BUSH_MAX_BERRIES, config.BERRY_NUTRIENT)
        self.radius = 20
        self.max_age = config.PLANT_MAX_AGE * random.uniform(0.8, 1.2)
        self.berry_offsets = [(int(self.radius * 0.6 * random.uniform(-1, 1)), int(self.radius * 0.6 * random.uniform(-1, 1))) for _ in range(config.BUSH_MAX_BERRIES)]

class WaterHole:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.frozen = False

class Burrow:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 8
        self.occupants = []
        self.food_stored = 0
        self.food_offsets = [(int((self.radius + 5) * random.uniform(-1, 1)), int((self.radius + 5) * random.uniform(-1, 1))) for _ in range(50)]

class River:
    def __init__(self, y, h):
        self.x = 0
        self.y = y
        self.w = config.SCREEN_WIDTH
        self.h = h

class World:
    def __init__(self):
        self.season = "summer"
        self.season_tick = 0
        self.trees = []
        self.bushes = []
        self.water_holes = []
        self.burrows = []
        self.river = River(config.SCREEN_HEIGHT // 2 - 25, 50)

        self.seeds = []

        self._init_plants(30, 30)
        self._init_water_holes(5)

    def _init_plants(self, num_trees, num_bushes):
        for _ in range(num_trees):
            x = random.randint(0, config.SCREEN_WIDTH)
            y = random.randint(0, config.SCREEN_HEIGHT)
            if not self.in_water(x, y):
                self.trees.append(Tree(x, y))
        for _ in range(num_bushes):
            x = random.randint(0, config.SCREEN_WIDTH)
            y = random.randint(0, config.SCREEN_HEIGHT)
            if not self.in_water(x, y):
                self.bushes.append(Bush(x, y))

    def _init_water_holes(self, num_holes):
        for _ in range(num_holes):
            x = random.randint(50, config.SCREEN_WIDTH - 50)
            y = random.randint(50, config.SCREEN_HEIGHT - 50)
            self.water_holes.append(WaterHole(x, y, random.randint(40, 80), random.randint(40, 80)))

    def in_water(self, x, y):
        if self.river.y <= y <= self.river.y + self.river.h:
            return True
        for wh in self.water_holes:
            if not wh.frozen:
                if (wh.x - wh.w//2) <= x <= (wh.x + wh.w//2) and (wh.y - wh.h//2) <= y <= (wh.y + wh.h//2):
                    return True
        return False

    def update(self):
        self.season_tick += 1
        if self.season_tick >= config.SEASON_LENGTH:
            self.season_tick = 0
            self._advance_season()

        # Update plants
        for tree in self.trees:
            tree.update()
        for bush in self.bushes:
            bush.update()

        self.trees = [t for t in self.trees if not t.dead]
        self.bushes = [b for b in self.bushes if not b.dead]

    def _advance_season(self):
        seasons = ["summer", "fall", "winter", "spring"]
        curr_idx = seasons.index(self.season)
        self.season = seasons[(curr_idx + 1) % 4]

        if self.season == "fall":
            # Trees plant seeds based on remaining leaves
            for tree in self.trees:
                num_seeds = tree.food_count // config.TREE_SEED_LEAF_INTERVAL
                for _ in range(num_seeds):
                    ox = random.randint(-60, 60)
                    oy = random.randint(-60, 60)
                    self.seeds.append(("tree", tree.x + ox, tree.y + oy))

        elif self.season == "winter":
            # 20% water holes freeze
            for wh in self.water_holes:
                if random.random() < 0.20:
                    wh.frozen = True

        elif self.season == "spring":
            # Seeds grow
            for seed_type, sx, sy in self.seeds:
                if 0 <= sx <= config.SCREEN_WIDTH and 0 <= sy <= config.SCREEN_HEIGHT:
                    if not self.in_water(sx, sy):
                        if seed_type == "tree":
                            self.trees.append(Tree(sx, sy))
                        elif seed_type == "bush":
                            self.bushes.append(Bush(sx, sy))
            self.seeds.clear()

            # Unfreeze water
            for wh in self.water_holes:
                wh.frozen = False

            # Plants grow food based on age (older grow more)
            for tree in self.trees:
                tree.grow(1.0 + (tree.age / config.PLANT_MAX_AGE))
            for bush in self.bushes:
                bush.grow(1.0 + (bush.age / config.PLANT_MAX_AGE))

    def get_bg_color(self):
        if self.season == "summer": return config.C_BG_SUMMER
        elif self.season == "fall": return config.C_BG_FALL
        elif self.season == "winter": return config.C_BG_WINTER
        else: return config.C_BG_SPRING

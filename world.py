import pygame
import random
import config
from math import sqrt


class SpatialHash:
    def __init__(self, cell_size=150):
        self.cell_size = cell_size
        self.grid = {}

    def _get_cell_coords(self, x, y):
        return int(x // self.cell_size), int(y // self.cell_size)

    def insert(self, entity):
        if not hasattr(entity, 'x') or not hasattr(entity, 'y'):
            return
        cell = self._get_cell_coords(entity.x, entity.y)
        if cell not in self.grid:
            self.grid[cell] = []
        self.grid[cell].append(entity)

    def clear(self):
        self.grid.clear()

    def get_nearby(self, x, y):
        cell_x, cell_y = self._get_cell_coords(x, y)
        nearby_entities = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                cell = (cell_x + dx, cell_y + dy)
                if cell in self.grid:
                    nearby_entities.extend(self.grid[cell])
        return nearby_entities

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

    def update(self, world):
        self.age += 1
        if self.age > self.max_age:
            self.dead = True



class Tree(Plant):
    def __init__(self, x, y):
        super().__init__(x, y, config.TREE_MAX_LEAVES, config.TREE_LEAF_NUTRIENT)
        self.radius = 15
        self.max_age = config.PLANT_MAX_AGE * random.uniform(0.8, 1.2)

    def update(self, world):
        super().update(world)
        if self.food_count <= 0 and world.season == "spring":
            self.dead = True

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
        self.food_offsets = [
            (int((self.radius + 5) * random.uniform(-1, 1)), int((self.radius + 5) * random.uniform(-1, 1)))
            for _ in range(config.BURROW_MAX_FOOD)
        ]

    def get_male(self):
        return next((o for o in self.occupants if getattr(o, 'gender', None) == 'male' and getattr(o, 'is_adult', False) and not getattr(o, 'dead', True)), None)

    def get_female(self):
        return next((o for o in self.occupants if getattr(o, 'gender', None) == 'female' and getattr(o, 'is_adult', False) and not getattr(o, 'dead', True)), None)

    def add_occupant(self, occupant):
        self.occupants.append(occupant)

    def remove_occupant(self, occupant):
        if occupant in self.occupants:
            self.occupants.remove(occupant)


class Carcass:
    def __init__(self, x, y, species):
        self.x = x
        self.y = y
        self.species = species
        if species == 'deer':
            self.nutrients, self.radius = 300, 12
        elif species == 'wolf':
            self.nutrients, self.radius = 150, 8
        else:
            self.nutrients, self.radius = 50, 5
        self.max_nutrients = self.nutrients
        self.dead = False

    def update(self):
        self.nutrients -= 0.05
        if self.nutrients <= 0:
            self.dead = True

    def eat(self, amount):
        eaten = min(amount, self.nutrients)
        self.nutrients -= eaten
        if self.nutrients <= 0:
            self.dead = True
        return eaten

class Nest:
    def __init__(self, tree):
        self.tree = tree
        self.x = tree.x
        self.y = tree.y
        self.occupants = []

class Egg:
    def __init__(self, x, y, species, parents):
        self.x = x
        self.y = y
        self.species = species
        self.parents = parents
        self.hatch_timer = config.SEASON_LENGTH
        self.dead = False

    def update(self):
        self.hatch_timer -= 1
        if self.hatch_timer <= 0:
            self.dead = True

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
        self.carcasses = []
        self.nests = []
        self.eggs = []
        self.river = River(config.SCREEN_HEIGHT // 2 - 25, 50)

        self.seeds = []

        self._init_plants(30, 40)
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
            tree.update(self)
        for bush in self.bushes:
            bush.update(self)
        for carcass in self.carcasses:
            carcass.update()
        for egg in self.eggs:
            egg.update()
            if egg.dead and len(egg.parents) == 2:
                import animals
                if egg.species == 'fish':
                    baby = animals.Fish(egg.x, egg.y, parents=egg.parents)
                elif egg.species == 'snake':
                    baby = animals.Snake(egg.x, egg.y, parents=egg.parents)
                elif egg.species == 'sparrow':
                    baby = animals.Sparrow(egg.x, egg.y, parents=egg.parents)
                elif egg.species == 'hawk':
                    baby = animals.Hawk(egg.x, egg.y, parents=egg.parents)
                else:
                    continue
                baby.mutate()
                if not hasattr(self, 'hatched_animals'):
                    self.hatched_animals = []
                self.hatched_animals.append(baby)


        self.nests = [n for n in self.nests if not n.tree.dead]
        self.trees = [t for t in self.trees if not t.dead]
        self.carcasses = [c for c in self.carcasses if not c.dead]
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

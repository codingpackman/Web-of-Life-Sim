import pygame
import sys
import os
import random
import config
from world import World
from animals import Rabbit, Deer, Wolf, Fish, Snake, Sparrow, Hawk

class Simulator:
    def __init__(self, headless=False):
        if headless:
            os.environ["SDL_VIDEODRIVER"] = "dummy"

        pygame.init()
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        pygame.display.set_caption("Ecosystem Simulator")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 24)

        self.world = World()
        self.world.spatial_hash = __import__('world').SpatialHash(cell_size=150)
        self.animals = []
        self._init_animals(10, 10, 10, 10, 5, 5, 3)

        self.running = True
        self.headless = headless

    def _init_animals(self, num_rabbits, num_deer, num_wolves, num_fish, num_snakes=5, num_sparrows=5, num_hawks=3):
        for _ in range(num_rabbits):
            x = random.randint(0, config.SCREEN_WIDTH)
            y = random.randint(0, config.SCREEN_HEIGHT)
            if not self.world.in_water(x, y):
                self.animals.append(Rabbit(x, y))

        for _ in range(num_deer):
            x = random.randint(0, config.SCREEN_WIDTH)
            y = random.randint(0, config.SCREEN_HEIGHT)
            if not self.world.in_water(x, y):
                self.animals.append(Deer(x, y))

        for _ in range(num_wolves):
            x = random.randint(0, config.SCREEN_WIDTH)
            y = random.randint(0, config.SCREEN_HEIGHT)
            if not self.world.in_water(x, y):
                self.animals.append(Wolf(x, y))

        for _ in range(num_fish):
            x = random.randint(0, config.SCREEN_WIDTH)
            y = random.randint(self.world.river.y, self.world.river.y + self.world.river.h)
            self.animals.append(Fish(x, y))

        for _ in range(num_snakes):
            x = random.randint(0, config.SCREEN_WIDTH)
            y = random.randint(0, config.SCREEN_HEIGHT)
            if not self.world.in_water(x, y):
                self.animals.append(Snake(x, y))

        for _ in range(num_sparrows):
            x = random.randint(0, config.SCREEN_WIDTH)
            y = random.randint(0, config.SCREEN_HEIGHT)
            self.animals.append(Sparrow(x, y))

        for _ in range(num_hawks):
            x = random.randint(0, config.SCREEN_WIDTH)
            y = random.randint(0, config.SCREEN_HEIGHT)
            self.animals.append(Hawk(x, y))

    def update(self):
        self.world.update()

        self.world.spatial_hash.clear()
        for entity in self.animals:
            self.world.spatial_hash.insert(entity)
        for entity in self.world.trees:
            self.world.spatial_hash.insert(entity)
        for entity in self.world.bushes:
            self.world.spatial_hash.insert(entity)

        for animal in self.animals:
            animal.update(self.world, self.animals)
            if getattr(animal, 'species', None) in ['wolf', 'snake', 'hawk']:
                animal.hunt(self.animals, self.world)

        if hasattr(self.world, 'hatched_animals') and self.world.hatched_animals:
            self.animals.extend(self.world.hatched_animals)
            self.world.hatched_animals.clear()

        self.world.eggs = [e for e in self.world.eggs if not e.dead]
        self.animals = [a for a in self.animals if not a.dead]

    def render(self):
        self.screen.fill(self.world.get_bg_color())

        season_tick = self.world.season_tick
        day_length = config.DAY_LENGTH
        darkness = 0
        if season_tick > day_length:
            night_tick = season_tick - day_length
            half_night = day_length / 2
            if night_tick < half_night:
                darkness = min(150, int((night_tick / half_night) * 150))
            else:
                darkness = min(150, int(((day_length - night_tick) / half_night) * 150))

        # Draw River
        pygame.draw.rect(self.screen, config.C_RIVER, (self.world.river.x, self.world.river.y, self.world.river.w, self.world.river.h))

        # Draw WaterHoles
        for wh in self.world.water_holes:
            color = config.C_FROZEN_WATER if wh.frozen else config.C_WATER
            pygame.draw.ellipse(self.screen, color, (wh.x - wh.w//2, wh.y - wh.h//2, wh.w, wh.h))

        # Draw Burrows
        for b in self.world.burrows:
            pygame.draw.circle(self.screen, config.C_BURROW, (int(b.x), int(b.y)), b.radius)
            # Draw tiny purple circles for stored food
            for i in range(b.food_stored):
                if i < len(b.food_offsets):
                    ox, oy = b.food_offsets[i]
                    pygame.draw.circle(self.screen, config.C_BERRY, (int(b.x + ox), int(b.y + oy)), 2)

        # Draw Bushes & Berries
        for bush in self.world.bushes:
            pygame.draw.circle(self.screen, config.C_BUSH, (int(bush.x), int(bush.y)), bush.radius)
            # Draw berries based on count
            for i in range(bush.food_count):
                if i < len(bush.berry_offsets):
                    ox, oy = bush.berry_offsets[i]
                    pygame.draw.circle(self.screen, config.C_BERRY, (int(bush.x + ox), int(bush.y + oy)), 2)

        # Draw Trees
        for tree in self.world.trees:
            pygame.draw.circle(self.screen, config.C_TREE, (int(tree.x), int(tree.y)), tree.radius)

        # Draw Animals
        for a in self.animals:
            color = config.C_RABBIT
            if a.species == 'deer': color = config.C_DEER
            elif a.species == 'wolf': color = config.C_WOLF
            elif a.species == 'fish': color = config.C_FISH
            elif a.species == 'snake': color = config.C_SNAKE
            elif a.species == 'sparrow': color = config.C_SPARROW
            elif a.species == 'hawk': color = config.C_HAWK

            if getattr(a, 'is_hidden', False):
                if a.species == 'rabbit':
                    color = (max(0, color[0] - 80), max(0, color[1] - 80), max(0, color[2] - 80))
                else:
                    continue

            if getattr(a, 'climbing_tree', None) is not None:
                # Make slightly transparent or just darker to indicate climbing
                color = (max(0, color[0] - 30), max(0, color[1] - 30), max(0, color[2] - 30))

            # draw baby indicator
            radius = a.radius if a.is_adult else a.radius * 0.6

            if getattr(a, 'flying', False):
                # Make it larger and slightly transparent to look like it's in the air
                radius *= 1.5
                fly_surface = pygame.Surface((int(radius*2), int(radius*2)), pygame.SRCALPHA)
                pygame.draw.circle(fly_surface, (*color, 200), (int(radius), int(radius)), int(radius))
                self.screen.blit(fly_surface, (int(a.x - radius), int(a.y - radius)))
            else:
                pygame.draw.circle(self.screen, color, (int(a.x), int(a.y)), int(radius))

        if darkness > 0:
            dark_surface = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
            dark_surface.set_alpha(darkness)
            dark_surface.fill((0, 0, 0))
            self.screen.blit(dark_surface, (0, 0))

        self.draw_ui()
        pygame.display.flip()

    def draw_ui(self):
        rabbits = sum(1 for a in self.animals if a.species == 'rabbit')
        deers = sum(1 for a in self.animals if a.species == 'deer')
        wolves = sum(1 for a in self.animals if a.species == 'wolf')

        ui_texts = [
            f"Season: {self.world.season.capitalize()} (Tick: {self.world.season_tick}/{config.SEASON_LENGTH})",
            f"Rabbits: {rabbits}",
            f"Deers: {deers}",
            f"Wolves: {wolves}",
            f"Trees: {len(self.world.trees)} | Bushes: {len(self.world.bushes)}"
        ]

        y_offset = 10
        for text in ui_texts:
            surf = self.font.render(text, True, (0, 0, 0))
            self.screen.blit(surf, (10, y_offset))
            y_offset += 25

    def run(self, ticks=None):
        tick_count = 0
        while self.running:
            if ticks and tick_count >= ticks:
                break

            if not self.headless:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False

            self.update()
            if not self.headless:
                self.render()
                self.clock.tick(config.FPS)

            tick_count += 1

        pygame.quit()

if __name__ == "__main__":
    sim = Simulator()
    sim.run()

import random
import math
import config

class AnimalAI:
    def __init__(self, species):
        self.species = species
        # Weights for different stimuli: (food, water, predator, prey, friend)
        self.weights = {
            'food': random.uniform(0.5, 1.5),
            'water': random.uniform(0.5, 1.5),
            'predator': random.uniform(-2.0, -1.0),
            'prey': random.uniform(1.0, 2.0),
            'friend': random.uniform(0.0, 0.5)
        }
        self.memory_map = {} # grid-based spatial memory
        self.grid_size = 50

    def get_grid_key(self, x, y):
        return (int(x // self.grid_size), int(y // self.grid_size))

    def update_memory(self, x, y, value_change):
        key = self.get_grid_key(x, y)
        if key not in self.memory_map:
            self.memory_map[key] = 0
        self.memory_map[key] += value_change
        # Learn from experience (Machine Learning lite)
        # Adapt weights slightly based on negative/positive reinforcement
        if value_change < 0: # Negative experience
            self.weights['predator'] *= 1.01 # Fear predators more
        elif value_change > 0:
            self.weights['food'] *= 1.01 # Value food more

    def get_location_value(self, x, y):
        key = self.get_grid_key(x, y)
        return self.memory_map.get(key, 0)

    def calculate_force(self, entity, world, animals):
        fx, fy = 0.0, 0.0

        # 1. Food attraction
        if entity.species in ['rabbit', 'deer']:
            # Herbivores seek plants
            closest_plant = None
            min_dist = float('inf')

            plants_to_check = []
            if entity.species == 'rabbit':
                plants_to_check = world.bushes
            else:
                plants_to_check = world.trees + world.bushes

            for plant in plants_to_check:
                if plant.food_count > 0:
                    dx = plant.x - entity.x
                    dy = plant.y - entity.y
                    dist = math.hypot(dx, dy)
                    if dist < min_dist:
                        min_dist = dist
                        closest_plant = plant

            if closest_plant and min_dist < 300:
                mult = max(0, (entity.max_hunger - entity.hunger) / entity.max_hunger)
                fx += (closest_plant.x - entity.x) / min_dist * self.weights['food'] * mult
                fy += (closest_plant.y - entity.y) / min_dist * self.weights['food'] * mult

        # 2. Water attraction
        water_mult = (entity.max_thirst - entity.thirst) / entity.max_thirst
        if entity.thirst < entity.max_thirst * 0.7:
            # River pull (vertical)
            if entity.y < world.river.y:
                fy += self.weights['water'] * water_mult
            elif entity.y > world.river.y + world.river.h:
                fy -= self.weights['water'] * water_mult
            # Waterhole pull
            for wh in world.water_holes:
                if not wh.frozen:
                    dx = wh.x - entity.x
                    dy = wh.y - entity.y
                    dist = math.hypot(dx, dy)
                    if dist < 300 and dist > 0:
                        fx += (dx / dist) * self.weights['water'] * water_mult
                        fy += (dy / dist) * self.weights['water'] * water_mult

        # 3. Predators & Prey & Friends
        for other in animals:
            if other == entity or other.dead: continue
            dx = other.x - entity.x
            dy = other.y - entity.y
            dist = math.hypot(dx, dy)

            if dist < 200 and dist > 0:
                if entity.species == 'wolf' and other.species in ['rabbit', 'deer']:
                    # Prey
                    fx += (dx / dist) * self.weights['prey']
                    fy += (dy / dist) * self.weights['prey']
                elif entity.species in ['rabbit', 'deer'] and other.species == 'wolf':
                    # Predator
                    fx += (dx / dist) * self.weights['predator']
                    fy += (dy / dist) * self.weights['predator']
                    entity.ai.update_memory(entity.x, entity.y, -1) # Negative association
                elif entity.species == other.species:
                    # Friend/Pack (Herd mentality)
                    fx += (dx / dist) * self.weights['friend']
                    fy += (dy / dist) * self.weights['friend']

        # Add random wander
        fx += random.uniform(-0.5, 0.5)
        fy += random.uniform(-0.5, 0.5)

        # Apply spatial memory bias
        mem_val = self.get_location_value(entity.x, entity.y)
        if mem_val < 0: # Danger area
            fx += random.uniform(-1, 1) # Panic jitter
            fy += random.uniform(-1, 1)

        # Normalize force
        mag = math.hypot(fx, fy)
        if mag > 0:
            fx /= mag
            fy /= mag

        return fx, fy

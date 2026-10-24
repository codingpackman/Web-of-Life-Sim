import random
import math
import config

class AnimalAI:
    def __init__(self, species, parents=None):
        self.species = species
        # Weights for different stimuli
        if parents and len(parents) == 2 and parents[0] and parents[1]:
            # Genetic crossover: average of parents + small mutation
            self.weights = {}
            for key in parents[0].ai.weights.keys():
                avg = (parents[0].ai.weights[key] + parents[1].ai.weights[key]) / 2.0
                mutation = random.uniform(0.9, 1.1)
                self.weights[key] = avg * mutation
        else:
            self.weights = {
                'food': random.uniform(0.5, 1.5),
                'water': random.uniform(0.5, 1.5),
                'predator': random.uniform(-2.0, -1.0),
                'prey': random.uniform(1.0, 2.0),
                'friend': random.uniform(0.0, 0.5),
                'separation': random.uniform(0.5, 1.5),
                'alignment': random.uniform(0.5, 1.5),
                'cohesion': random.uniform(0.5, 1.5),
                'burrow': random.uniform(1.0, 2.0) if species == 'rabbit' else 0.0
            }
        self.memory_map = {} # grid-based spatial memory: {'danger': 0, 'food': 0, 'water': 0}
        self.grid_size = 50

    def get_grid_key(self, x, y):
        return (int(x // self.grid_size), int(y // self.grid_size))

    def update_memory(self, x, y, value_change, stimulus_type='danger'):
        key = self.get_grid_key(x, y)
        if key not in self.memory_map:
            self.memory_map[key] = {'danger': 0.0, 'food': 0.0, 'water': 0.0}
        self.memory_map[key][stimulus_type] += value_change

        # Learn from experience (Machine Learning lite)
        if stimulus_type == 'danger' and value_change > 0: # More danger
            self.weights['predator'] *= 1.01
        elif stimulus_type == 'food' and value_change > 0:
            self.weights['food'] *= 1.01

    def decay_memory(self):
        for key in self.memory_map:
            for channel in self.memory_map[key]:
                self.memory_map[key][channel] *= 0.99

    def get_location_memory(self, x, y):
        key = self.get_grid_key(x, y)
        return self.memory_map.get(key, {'danger': 0.0, 'food': 0.0, 'water': 0.0})

    def calculate_force(self, entity, world, animals):
        fx, fy = 0.0, 0.0

        # Dynamic weights based on FSM state
        current_food_weight = self.weights['food']
        current_predator_weight = self.weights['predator']

        if getattr(entity, 'state', 'FORAGING') == 'FLEEING':
            current_food_weight = 0.0
            current_predator_weight *= 3.0

            if entity.species == 'rabbit' and hasattr(entity, 'home_burrow') and entity.home_burrow:
                # Strong attraction to burrow while fleeing
                bdx = entity.home_burrow.x - entity.x
                bdy = entity.home_burrow.y - entity.y
                bdist = math.hypot(bdx, bdy)
                if bdist > 0:
                    fx += (bdx / bdist) * self.weights['burrow'] * 5.0

        # 1. Food attraction
        if entity.species in ['rabbit', 'deer'] and current_food_weight > 0:
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
                hunger_force = 3.0 if mult > 0.5 else 1.0
                fx += (closest_plant.x - entity.x) / min_dist * current_food_weight * mult * hunger_force
                fy += (closest_plant.y - entity.y) / min_dist * current_food_weight * mult * hunger_force

        # 2. Water attraction
        water_mult = (entity.max_thirst - entity.thirst) / entity.max_thirst
        thirst_force = 3.0 if water_mult > 0.5 else 1.0
        if entity.thirst < entity.max_thirst * 0.7:
            # River pull (vertical)
            if entity.y < world.river.y:
                fy += self.weights['water'] * water_mult * thirst_force
            elif entity.y > world.river.y + world.river.h:
                fy -= self.weights['water'] * water_mult * thirst_force
            # Waterhole pull
            for wh in world.water_holes:
                if not wh.frozen:
                    dx = wh.x - entity.x
                    dy = wh.y - entity.y
                    dist = math.hypot(dx, dy)
                    if dist < 300 and dist > 0:
                        fx += (dx / dist) * self.weights['water'] * water_mult * thirst_force
                        fy += (dy / dist) * self.weights['water'] * water_mult * thirst_force

        # 3. Predators & Prey & Friends (including Boids)
        boids_neighbors = 0
        avg_vx, avg_vy = 0.0, 0.0
        center_x, center_y = 0.0, 0.0

        for other in animals:
            if other == entity or other.dead: continue
            dx = other.x - entity.x
            dy = other.y - entity.y
            dist = math.hypot(dx, dy)

            if dist < 200 and dist > 0:
                if entity.species == 'wolf' and other.species in ['rabbit', 'deer']:
                    # Prey - Predictive Pathing
                    target_x = other.x + other.vx * 10
                    target_y = other.y + other.vy * 10
                    pdx = target_x - entity.x
                    pdy = target_y - entity.y
                    pdist = math.hypot(pdx, pdy)
                    if pdist > 0:
                        fx += (pdx / pdist) * self.weights['prey']
                        fy += (pdy / pdist) * self.weights['prey']
                elif entity.species in ['rabbit', 'deer'] and other.species == 'wolf':
                    # Predator
                    fx += (dx / dist) * current_predator_weight
                    fy += (dy / dist) * current_predator_weight
                    entity.ai.update_memory(entity.x, entity.y, 5, 'danger') # Negative association
                elif entity.species == other.species:
                    if entity.species == 'wolf':
                        # Wolf Flanking (Separation overrides herding)
                        if dist < 100:
                            fx -= (dx / dist) * self.weights['separation']
                            fy -= (dy / dist) * self.weights['separation']
                    else:
                        # Friend/Pack (Herd mentality - Boids) for herbivores
                        boids_neighbors += 1
                        avg_vx += other.vx
                        avg_vy += other.vy
                        center_x += other.x
                        center_y += other.y

                        if dist < 50:
                            # Separation
                            fx -= (dx / dist) * self.weights['separation']
                            fy -= (dy / dist) * self.weights['separation']

        if boids_neighbors > 0:
            avg_vx /= boids_neighbors
            avg_vy /= boids_neighbors
            center_x /= boids_neighbors
            center_y /= boids_neighbors

            # Alignment
            if math.hypot(avg_vx, avg_vy) > 0:
                mag = math.hypot(avg_vx, avg_vy)
                fx += (avg_vx / mag) * self.weights['alignment']
                fy += (avg_vy / mag) * self.weights['alignment']

            # Cohesion
            cdx = center_x - entity.x
            cdy = center_y - entity.y
            cdist = math.hypot(cdx, cdy)
            if cdist > 0:
                fx += (cdx / cdist) * self.weights['cohesion']
                fy += (cdy / cdist) * self.weights['cohesion']

        # Add random wander
        fx += random.uniform(-0.5, 0.5)
        fy += random.uniform(-0.5, 0.5)

        # Wall repulsion
        if entity.x < 50:
            fx += 2.0
        elif entity.x > config.SCREEN_WIDTH - 50:
            fx -= 2.0
        if entity.y < 50:
            fy += 2.0
        elif entity.y > config.SCREEN_HEIGHT - 50:
            fy -= 2.0

        # Apply spatial memory bias
        mem_vals = self.get_location_memory(entity.x, entity.y)
        if mem_vals['danger'] > 0: # Danger area
            fx += random.uniform(-1, 1) * mem_vals['danger'] # Panic jitter
            fy += random.uniform(-1, 1) * mem_vals['danger']
        if mem_vals['food'] > 0:
            # add small bias towards current center of grid, very rough
            grid_center_x = (entity.x // self.grid_size) * self.grid_size + self.grid_size / 2
            grid_center_y = (entity.y // self.grid_size) * self.grid_size + self.grid_size / 2
            dx, dy = grid_center_x - entity.x, grid_center_y - entity.y
            dist = math.hypot(dx, dy)
            if dist > 0:
                fx += (dx / dist) * mem_vals['food'] * 0.5
                fy += (dy / dist) * mem_vals['food'] * 0.5

        # Normalize force
        mag = math.hypot(fx, fy)
        if mag > 0:
            fx /= mag
            fy /= mag

        return fx, fy

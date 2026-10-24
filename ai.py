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

        # Generational Memory Transfer
        if parents and len(parents) == 2 and parents[0] and parents[1]:
            parent_maps = [parents[0].ai.memory_map, parents[1].ai.memory_map]
            for p_map in parent_maps:
                for key, val in p_map.items():
                    if key not in self.memory_map:
                        self.memory_map[key] = {'danger': 0.0, 'food': 0.0, 'water': 0.0}
                    self.memory_map[key]['danger'] += val['danger'] * 0.25
                    self.memory_map[key]['food'] += val['food'] * 0.25
                    self.memory_map[key]['water'] += val['water'] * 0.25

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

        # Survival Overrides (Critical Thresholds)
        hunger_ratio = entity.hunger / entity.max_hunger
        thirst_ratio = entity.thirst / entity.max_thirst

        if hunger_ratio < 0.2:
            entity.state = "STARVING"
        elif thirst_ratio < 0.2:
            entity.state = "DEHYDRATED"
        elif entity.state in ["STARVING", "DEHYDRATED"]:
            entity.state = "FORAGING"

        # Dynamic weights based on FSM state
        current_food_weight = self.weights['food']
        current_predator_weight = self.weights['predator']
        current_water_weight = self.weights['water']
        herd_multiplier = 1.0

        if entity.state == "STARVING":
            current_food_weight *= 10.0
            herd_multiplier = 0.0
        elif entity.state == "DEHYDRATED":
            current_water_weight *= 10.0
            herd_multiplier = 0.0

        # Protective Herding logic (Adult male deer overriding state)
        if entity.species == 'deer' and entity.gender == 'male' and entity.is_adult and entity.state not in ["STARVING", "DEHYDRATED"]:
            baby_in_danger = False
            for other in animals:
                if other.species == 'deer' and not other.is_adult and not other.dead:
                    if math.hypot(other.x - entity.x, other.y - entity.y) < 150:
                        # Check for wolf near baby
                        for wolf in animals:
                            if wolf.species == 'wolf' and not wolf.dead:
                                if math.hypot(wolf.x - other.x, wolf.y - other.y) < 150:
                                    baby_in_danger = True
                                    break
                        if baby_in_danger:
                            break
            if baby_in_danger:
                entity.state = "AGGRESSIVE"
            elif entity.state == "AGGRESSIVE":
                entity.state = "FORAGING"

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

        if getattr(entity, 'state', 'FORAGING') == 'HOARDING':
            current_food_weight *= 2.0
            if entity.species == 'rabbit' and hasattr(entity, 'home_burrow') and entity.home_burrow and entity.carried_food >= 5:
                # Strong attraction to burrow to deposit food
                current_food_weight = 0.0 # Don't go for food anymore
                bdx = entity.home_burrow.x - entity.x
                bdy = entity.home_burrow.y - entity.y
                bdist = math.hypot(bdx, bdy)
                if bdist > 0:
                    fx += (bdx / bdist) * self.weights['burrow'] * 3.0

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

        # Water Repulsion if full
        if entity.thirst >= entity.max_thirst * 0.95 and world.in_water(entity.x, entity.y):
            current_water_weight = -2.0
            if entity.y >= world.river.y and entity.y <= world.river.y + world.river.h:
                if entity.y < world.river.y + world.river.h / 2:
                    fy -= 5.0 # Push up out of river
                else:
                    fy += 5.0 # Push down out of river
            else:
                for wh in world.water_holes:
                    if not wh.frozen:
                        if (wh.x - wh.w//2) <= entity.x <= (wh.x + wh.w//2) and (wh.y - wh.h//2) <= entity.y <= (wh.y + wh.h//2):
                            dx = entity.x - wh.x
                            dy = entity.y - wh.y
                            dist = math.hypot(dx, dy)
                            if dist > 0:
                                fx += (dx / dist) * 5.0
                                fy += (dy / dist) * 5.0

        if entity.thirst < entity.max_thirst * 0.7:
            # River pull (vertical)
            if entity.y < world.river.y:
                fy += current_water_weight * water_mult * thirst_force
            elif entity.y > world.river.y + world.river.h:
                fy -= current_water_weight * water_mult * thirst_force
            # Waterhole pull
            for wh in world.water_holes:
                if not wh.frozen:
                    dx = wh.x - entity.x
                    dy = wh.y - entity.y
                    dist = math.hypot(dx, dy)
                    if dist < 300 and dist > 0:
                        fx += (dx / dist) * current_water_weight * water_mult * thirst_force
                        fy += (dy / dist) * current_water_weight * water_mult * thirst_force

        # 3. Predators & Prey & Friends (including Boids)
        boids_neighbors = 0
        avg_vx, avg_vy = 0.0, 0.0
        center_x, center_y = 0.0, 0.0

        # Wolf Attention Span Logic
        if entity.species == 'wolf':
            if getattr(entity, 'wander_timer', 0) > 0:
                entity.state = "WANDERING"
                entity.chase_target = None
            else:
                entity.state = "HUNTING"
                # Determine target if not set or target invalid
                if not entity.chase_target or entity.chase_target.dead or getattr(entity.chase_target, 'is_hidden', False) or entity.chase_target in getattr(entity, 'ignored_prey', {}):
                    best_target = None
                    best_dist = float('inf')
                    for a in animals:
                        if a.species in ['rabbit', 'deer'] and not a.dead and not getattr(a, 'is_hidden', False) and a not in getattr(entity, 'ignored_prey', {}):
                            d = math.hypot(a.x - entity.x, a.y - entity.y)
                            if d < 300 and d < best_dist:
                                best_dist = d
                                best_target = a
                    if best_target:
                        entity.chase_target = best_target
                        entity.chase_timer = 0

                if entity.chase_target:
                    entity.chase_timer += 1
                    if entity.chase_timer > 300: # 5 seconds
                        # Drop target
                        if hasattr(entity, 'ignored_prey'):
                            entity.ignored_prey[entity.chase_target] = 1200 # Ignore for 20 seconds
                        entity.chase_target = None
                        entity.wander_timer = 300 # Wander for 5 seconds

        for other in animals:
            if other == entity or other.dead: continue
            dx = other.x - entity.x
            dy = other.y - entity.y
            dist = math.hypot(dx, dy)

            if dist < 200 and dist > 0:
                if entity.species == 'wolf' and other.species in ['rabbit', 'deer']:
                    # Prey - Predictive Pathing (only if it's the chase target or if wandering, ignore)
                    if entity.state != "WANDERING" and other == entity.chase_target:
                        target_x = other.x + other.vx * 10
                        target_y = other.y + other.vy * 10
                        pdx = target_x - entity.x
                        pdy = target_y - entity.y
                        pdist = math.hypot(pdx, pdy)
                        if pdist > 0:
                            fx += (pdx / pdist) * self.weights['prey']
                            fy += (pdy / pdist) * self.weights['prey']
                    # Wolf repelled by aggressive deer
                    if other.species == 'deer' and getattr(other, 'state', '') == 'AGGRESSIVE':
                        fx -= (dx / dist) * self.weights['prey'] * 2.0
                        fy -= (dy / dist) * self.weights['prey'] * 2.0
                elif entity.species in ['rabbit', 'deer'] and other.species == 'wolf':
                    # Predator
                    if entity.state == "AGGRESSIVE":
                        # Rush the wolf to push it away
                        fx += (dx / dist) * abs(current_predator_weight) * 2.0
                        fy += (dy / dist) * abs(current_predator_weight) * 2.0
                    else:
                        fx += (dx / dist) * current_predator_weight
                        fy += (dy / dist) * current_predator_weight
                        entity.ai.update_memory(entity.x, entity.y, 5, 'danger') # Negative association
                elif entity.species == other.species:
                    if entity.species == 'wolf':
                        # Wolf Pack (Herd mentality - Boids) for wolves
                        if boids_neighbors < 3: # Small pack limit
                            boids_neighbors += 1
                            avg_vx += other.vx
                            avg_vy += other.vy
                            center_x += other.x
                            center_y += other.y

                        # Wolf Flanking (Separation)
                        if dist < 100:
                            fx -= (dx / dist) * self.weights['separation']
                            fy -= (dy / dist) * self.weights['separation']
                    else:
                        # Friend/Pack (Herd mentality - Boids) for herbivores
                        # Strict herd caps (3 to 4 neighbors)
                        herd_cap = 4
                        if boids_neighbors < herd_cap:
                            boids_neighbors += 1
                            avg_vx += other.vx
                            avg_vy += other.vy
                            center_x += other.x
                            center_y += other.y

                        if dist < 50:
                            # Separation
                            sep_weight = self.weights['separation']
                            # If adult male deer near baby, drop separation to keep them tight
                            if entity.species == 'deer' and entity.gender == 'male' and entity.is_adult and not other.is_adult:
                                sep_weight = 0.0

                            if sep_weight > 0:
                                fx -= (dx / dist) * sep_weight
                                fy -= (dy / dist) * sep_weight

        if boids_neighbors > 0:
            avg_vx /= boids_neighbors
            avg_vy /= boids_neighbors
            center_x /= boids_neighbors
            center_y /= boids_neighbors

            # Alignment
            if math.hypot(avg_vx, avg_vy) > 0:
                mag = math.hypot(avg_vx, avg_vy)
                fx += (avg_vx / mag) * self.weights['alignment'] * herd_multiplier
                fy += (avg_vy / mag) * self.weights['alignment'] * herd_multiplier

            # Cohesion
            cdx = center_x - entity.x
            cdy = center_y - entity.y
            cdist = math.hypot(cdx, cdy)
            if cdist > 0:
                fx += (cdx / cdist) * self.weights['cohesion'] * herd_multiplier
                fy += (cdy / cdist) * self.weights['cohesion'] * herd_multiplier

        # Add random wander
        fx += random.uniform(-0.5, 0.5)
        fy += random.uniform(-0.5, 0.5)

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

        # Territory Establishment (Home Ranges)
        if hunger_ratio > 0.8 and thirst_ratio > 0.8:
            if getattr(entity, 'home_range', None) is None:
                entity.home_range = (entity.x, entity.y)

        if getattr(entity, 'home_range', None) is not None:
            hrx, hry = entity.home_range
            dist_to_hr = math.hypot(hrx - entity.x, hry - entity.y)
            if dist_to_hr > 200:
                fx += (hrx - entity.x) / dist_to_hr * 0.5
                fy += (hry - entity.y) / dist_to_hr * 0.5

        if entity.species == 'deer':
            wander_weight = getattr(entity, 'wanderlust_weight', 0.0)
            if wander_weight > 0:
                # Use perlin-like noise or persistent random direction for wanderlust
                if not hasattr(entity, 'wander_dir_x') or random.random() < 0.02:
                    entity.wander_dir_x = random.uniform(-1, 1)
                    entity.wander_dir_y = random.uniform(-1, 1)

                # Normalize wander dir
                wdir_mag = math.hypot(entity.wander_dir_x, entity.wander_dir_y)
                if wdir_mag > 0:
                    entity.wander_dir_x /= wdir_mag
                    entity.wander_dir_y /= wdir_mag

                fx += entity.wander_dir_x * wander_weight
                fy += entity.wander_dir_y * wander_weight

        # Normalize force
        mag = math.hypot(fx, fy)
        if mag > 0:
            fx /= mag
            fy /= mag

        return fx, fy

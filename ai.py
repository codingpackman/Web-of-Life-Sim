import random
import math
import config
import world as world_mod
import math

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
        self.memory_map = {} # grid-based spatial memory: {'danger_day': 0, 'danger_night': 0, 'food': 0, 'water': 0}
        self.grid_size = 50

        # Generational Memory Transfer
        if parents and len(parents) == 2 and parents[0] and parents[1]:
            parent_maps = [parents[0].ai.memory_map, parents[1].ai.memory_map]
            for p_map in parent_maps:
                for key, val in p_map.items():
                    if key not in self.memory_map:
                        self.memory_map[key] = {'danger_day': 0.0, 'danger_night': 0.0, 'food': 0.0, 'water': 0.0}
                    self.memory_map[key]['danger_day'] += val['danger_day'] * 0.25
                    self.memory_map[key]['danger_night'] += val['danger_night'] * 0.25
                    self.memory_map[key]['food'] += val['food'] * 0.25
                    self.memory_map[key]['water'] += val['water'] * 0.25

    def get_grid_key(self, x, y):
        return (int(x // self.grid_size), int(y // self.grid_size))

    def update_memory(self, x, y, value_change, stimulus_type='danger', is_night=False):
        key = self.get_grid_key(x, y)
        if key not in self.memory_map:
            self.memory_map[key] = {'danger_day': 0.0, 'danger_night': 0.0, 'food': 0.0, 'water': 0.0}


        # Learn from experience (Machine Learning lite)
        # Handle temporal splitting
        real_stimulus = 'danger_night' if stimulus_type == 'danger' and is_night else ('danger_day' if stimulus_type == 'danger' else stimulus_type)
        self.memory_map[key][real_stimulus] += value_change

        if stimulus_type == 'danger' and value_change > 0:
            self.weights['predator'] *= 1.01
        elif stimulus_type == 'food' and value_change > 0:
            self.weights['food'] *= 1.01

    def decay_memory(self):
        for key in self.memory_map:
            for channel in self.memory_map[key]:
                self.memory_map[key][channel] *= 0.99

    def get_location_memory(self, x, y):
        key = self.get_grid_key(x, y)
        return self.memory_map.get(key, {'danger_day': 0.0, 'danger_night': 0.0, 'food': 0.0, 'water': 0.0})

    @staticmethod
    def _are_deer_family(a, b):
        a_parents = getattr(a, 'parents', None) or []
        b_parents = getattr(b, 'parents', None) or []
        return (
            b in a_parents
            or a in b_parents
            or any(parent in b_parents for parent in a_parents)
            or getattr(a, 'mate', None) is b
            or getattr(b, 'mate', None) is a
            or any(getattr(parent, 'mate', None) is b for parent in a_parents)
            or any(getattr(parent, 'mate', None) is a for parent in b_parents)
        )

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

        if getattr(entity, 'dive_target', None):
            dx = entity.dive_target.x - entity.x
            dy = entity.dive_target.y - entity.y
            dist_sq = dx**2 + dy**2
            if dist_sq > 0:
                dist = math.sqrt(dist_sq)
                target_fx = dx / dist
                target_fy = dy / dist

                # Severe dampening (cannot turn fast)
                # We blend the new target force with the current velocity vector heavily biased to velocity
                mag_v = math.sqrt(entity.vx**2 + entity.vy**2)
                if mag_v > 0:
                    current_fx = entity.vx / mag_v
                    current_fy = entity.vy / mag_v
                else:
                    current_fx, current_fy = target_fx, target_fy

                current_angle = math.atan2(current_fy, current_fx)
                target_angle = math.atan2(target_fy, target_fx)
                angle_delta = (target_angle - current_angle + math.pi) % math.tau - math.pi
                max_turn = math.radians(config.HAWK_DIVE_TURN_RATE_DEGREES)
                angle = current_angle + max(-max_turn, min(max_turn, angle_delta))
                return math.cos(angle), math.sin(angle)

        if entity.species == 'sparrow' and getattr(entity, 'flying', False):
            target = getattr(entity, 'flight_target', None)
            if target:
                dx = target[0] - entity.x
                dy = target[1] - entity.y
                distance = math.hypot(dx, dy)
                if distance > 0:
                    return dx / distance, dy / distance

        if entity.species == 'hawk' and getattr(entity, 'flying', False):
            target = getattr(entity, 'flight_target', None)
            if target:
                dx = target[0] - entity.x
                dy = target[1] - entity.y
                distance = math.hypot(dx, dy)
                if distance > 0:
                    return dx / distance, dy / distance

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
            if (
                entity.species == 'rabbit'
                and getattr(entity, 'home_burrow', None)
                and entity.carried_food >= 5
                and entity.home_burrow.food_stored < config.BURROW_MAX_FOOD
            ):
                # Strong attraction to burrow to deposit food
                current_food_weight = 0.0 # Don't go for food anymore
                bdx = entity.home_burrow.x - entity.x
                bdy = entity.home_burrow.y - entity.y
                bdist = math.hypot(bdx, bdy)
                if bdist > 0:
                    fx += (bdx / bdist) * self.weights['burrow'] * 3.0

        if entity.species == 'rabbit' and getattr(entity, 'home_burrow', None):
            bdx = entity.home_burrow.x - entity.x
            bdy = entity.home_burrow.y - entity.y
            bdist = math.hypot(bdx, bdy)
            if bdist > config.RABBIT_BURROW_RANGE:
                range_pressure = min(
                    2.5,
                    1.0 + (bdist - config.RABBIT_BURROW_RANGE) / 100,
                )
                fx += (bdx / bdist) * range_pressure
                fy += (bdy / bdist) * range_pressure

        if (
            entity.species == 'rabbit'
            and getattr(entity, 'home_burrow', None)
            and entity.home_burrow.food_stored > 0
            and entity.hunger < entity.max_hunger
        ):
            bdx = entity.home_burrow.x - entity.x
            bdy = entity.home_burrow.y - entity.y
            bdist = math.hypot(bdx, bdy)
            if 0 < bdist < 350:
                fx += (bdx / bdist) * self.weights['burrow'] * 3.0

        # 1. Food attraction
        if entity.species in ['rabbit', 'deer', 'sparrow'] and current_food_weight > 0:
            # Herbivores seek plants
            closest_plant = None
            min_dist = float('inf')

            plants_to_check = []
            if entity.species in ['rabbit', 'sparrow']:
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

            if closest_plant and 0 < min_dist < 300:
                mult = max(0, (entity.max_hunger - entity.hunger) / entity.max_hunger)
                if (
                    entity.species == 'rabbit'
                    and getattr(entity, 'home_burrow', None)
                    and entity.carried_food < 5
                    and entity.home_burrow.food_stored + entity.carried_food < config.BURROW_MAX_FOOD
                ):
                    mult = max(mult, 1.0)
                if entity.species == 'sparrow' and entity.hunger < entity.max_hunger * 0.9:
                    mult = max(mult, 1.0)
                hunger_force = 4.0 if entity.species == 'sparrow' and mult > 0 else (3.0 if mult > 0.5 else 1.0)
                fx += (closest_plant.x - entity.x) / min_dist * current_food_weight * mult * hunger_force
                fy += (closest_plant.y - entity.y) / min_dist * current_food_weight * mult * hunger_force

        # 2. Water attraction
        water_mult = (entity.max_thirst - entity.thirst) / entity.max_thirst
        thirst_force = 3.0 if water_mult > 0.5 else 1.0

        # Water Repulsion if full
        if (
            entity.species != 'fish'
            and entity.thirst >= entity.max_thirst * 0.95
            and world.in_water(entity.x, entity.y)
        ):
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

        if entity.species != 'fish' and entity.thirst < entity.max_thirst * 0.7:
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
        if entity.species == 'wolf':
            social_neighbors = [
                other for other in animals
                if other is not entity
                and not other.dead
                and other.species == 'wolf'
                and math.hypot(other.x - entity.x, other.y - entity.y) < 200
            ][:3]
        elif entity.species == 'deer':
            social_neighbors = sorted(
                (
                    other for other in animals
                    if other is not entity
                    and not other.dead
                    and other.species == 'deer'
                    and self._are_deer_family(entity, other)
                    and math.hypot(other.x - entity.x, other.y - entity.y) < 200
                ),
                key=lambda other: math.hypot(other.x - entity.x, other.y - entity.y),
            )[:2]
        else:
            social_neighbors = []

        boids_neighbors = len(social_neighbors)
        for other in social_neighbors:
            avg_vx += other.vx
            avg_vy += other.vy
            center_x += other.x
            center_y += other.y

        # Wolf Attention Span Logic
        if entity.species == 'wolf':
            if (
                entity.hunger >= entity.max_hunger * 0.9
                or getattr(entity, 'feeding_cooldown', 0) > 0
            ):
                entity.state = "WANDERING"
                entity.chase_target = None
            elif getattr(entity, 'wander_timer', 0) > 0:
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

            if dist == 0 and other.species == entity.species and entity.species in ['rabbit', 'deer']:
                separation = self.weights['separation']
                if entity.species == 'rabbit':
                    separation *= 1.5
                angle = random.uniform(0, math.tau)
                fx += math.cos(angle) * separation
                fy += math.sin(angle) * separation

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
                elif (
                    entity.species == 'snake'
                    and other.species == 'fish'
                    and getattr(other, 'underwater', False)
                    and entity.hunger < entity.max_hunger * 0.9
                ):
                    fx += (dx / dist) * self.weights['prey']
                    fy += (dy / dist) * self.weights['prey']
                elif (
                    entity.species in ['rabbit', 'deer']
                    and (
                        other.species == 'wolf'
                        or (entity.species == 'rabbit' and other.species == 'snake')
                    )
                ):
                    # Predator
                    if entity.state == "AGGRESSIVE":
                        # Rush the wolf to push it away
                        fx += (dx / dist) * abs(current_predator_weight) * 2.0
                        fy += (dy / dist) * abs(current_predator_weight) * 2.0
                    else:
                        fx += (dx / dist) * current_predator_weight
                        fy += (dy / dist) * current_predator_weight
                        entity.ai.update_memory(entity.x, entity.y, 5, 'danger') # Negative association
                elif entity.species == 'sparrow' and other.species in ['hawk', 'snake', 'wolf']:
                    if dist < 180 and not getattr(entity, 'is_hidden', False):
                        escape_weight = 4.0 if entity.flying else 2.0
                        fx -= (dx / dist) * escape_weight
                        fy -= (dy / dist) * escape_weight
                elif entity.species == 'fish' and other.species in ['hawk', 'snake']:
                    if dist < 140:
                        escape_weight = 8.0 * (1 - dist / 140)
                        fx -= (dx / dist) * escape_weight
                        fy -= (dy / dist) * escape_weight
                elif entity.species == other.species:
                    separation_range = 100 if entity.species == 'wolf' else 35
                    if dist < separation_range:
                        separation = self.weights['separation']
                        if entity.species == 'rabbit':
                            separation *= 1.5
                        fx -= (dx / dist) * separation
                        fy -= (dy / dist) * separation

        if boids_neighbors > 0:
            avg_vx /= boids_neighbors
            avg_vy /= boids_neighbors
            center_x /= boids_neighbors
            center_y /= boids_neighbors

            # Alignment
            if math.hypot(avg_vx, avg_vy) > 0:
                mag = math.hypot(avg_vx, avg_vy)
                social_weight = 0.2 if entity.species == 'deer' else 1.0
                fx += (avg_vx / mag) * self.weights['alignment'] * herd_multiplier * social_weight
                fy += (avg_vy / mag) * self.weights['alignment'] * herd_multiplier * social_weight

            # Cohesion
            cdx = center_x - entity.x
            cdy = center_y - entity.y
            cdist = math.hypot(cdx, cdy)
            if cdist > 0:
                social_weight = 0.2 if entity.species == 'deer' else 1.0
                fx += (cdx / cdist) * self.weights['cohesion'] * herd_multiplier * social_weight
                fy += (cdy / cdist) * self.weights['cohesion'] * herd_multiplier * social_weight

        if entity.species == 'deer' and entity.state not in ["STARVING", "DEHYDRATED", "FLEEING"]:
            group_activities = [
                other for other in animals
                if other is not entity
                and not other.dead
                and other.species == 'deer'
                and self._are_deer_family(entity, other)
                and other.activity_timer > 0
                and other.activity_target is not None
                and other.current_activity in {"drinking", "eating"}
                and math.hypot(other.x - entity.x, other.y - entity.y) < 250
                and (
                    (other.current_activity == "drinking" and entity.thirst < entity.max_thirst * 0.95)
                    or (other.current_activity == "eating" and entity.hunger < entity.max_hunger)
                )
            ]
            if group_activities:
                activity_leader = min(
                    group_activities,
                    key=lambda other: math.hypot(other.x - entity.x, other.y - entity.y),
                )
                target_x, target_y = activity_leader.activity_target
                adx, ady = target_x - entity.x, target_y - entity.y
                adist = math.hypot(adx, ady)
                if adist > 0:
                    fx += (adx / adist) * 2.0
                    fy += (ady / adist) * 2.0

        # Add random wander
        fx += random.uniform(-0.5, 0.5)
        fy += random.uniform(-0.5, 0.5)

        # Apply spatial memory bias
        mem_vals = self.get_location_memory(entity.x, entity.y)
        is_night_now = getattr(world, 'season_tick', 0) > config.DAY_LENGTH
        current_danger = mem_vals['danger_night'] if is_night_now else mem_vals['danger_day']
        if current_danger > 0:
            fx += random.uniform(-1, 1) * current_danger
            fy += random.uniform(-1, 1) * current_danger
        if mem_vals['food'] > 0:
            # add small bias towards current center of grid, very rough
            grid_center_x = (entity.x // self.grid_size) * self.grid_size + self.grid_size / 2
            grid_center_y = (entity.y // self.grid_size) * self.grid_size + self.grid_size / 2
            dx, dy = grid_center_x - entity.x, grid_center_y - entity.y
            dist = math.hypot(dx, dy)
            if dist > 0:
                fx += (dx / dist) * mem_vals['food'] * 0.5
                fy += (dy / dist) * mem_vals['food'] * 0.5

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

        if entity.species == 'fish':
            margin = entity.radius + 12
            if entity.x < margin + 40:
                fx += (margin + 40 - entity.x) / 40 * 3.0
            elif entity.x > config.SCREEN_WIDTH - margin - 40:
                fx -= (entity.x - (config.SCREEN_WIDTH - margin - 40)) / 40 * 3.0
            river = world.river
            bank_buffer = 10
            safe_top = river.y + entity.radius + 2 + bank_buffer
            safe_bottom = river.y + river.h - entity.radius - 2 - bank_buffer
            if entity.y < safe_top:
                fy += (safe_top - entity.y) / bank_buffer * 2.0
            elif entity.y > safe_bottom:
                fy -= (entity.y - safe_bottom) / bank_buffer * 2.0
        else:
            if entity.species == 'deer':
                margin = entity.radius + 80
                if entity.x < margin:
                    fx += (margin - entity.x) / 80 * 6.0
                elif entity.x > config.SCREEN_WIDTH - margin:
                    fx -= (entity.x - (config.SCREEN_WIDTH - margin)) / 80 * 6.0
                if entity.y < margin:
                    fy += (margin - entity.y) / 80 * 6.0
                elif entity.y > config.SCREEN_HEIGHT - margin:
                    fy -= (entity.y - (config.SCREEN_HEIGHT - margin)) / 80 * 6.0
            else:
                margin = entity.radius + 12
                if entity.x < margin:
                    fx += (margin - entity.x) / margin * 2.0
                elif entity.x > config.SCREEN_WIDTH - margin:
                    fx -= (entity.x - (config.SCREEN_WIDTH - margin)) / margin * 2.0
                if entity.y < margin:
                    fy += (margin - entity.y) / margin * 2.0
                elif entity.y > config.SCREEN_HEIGHT - margin:
                    fy -= (entity.y - (config.SCREEN_HEIGHT - margin)) / margin * 2.0

        # Keep animals exploring in a steady direction instead of relying on
        # tick-to-tick random jitter, which can be canceled by herd forces.
        entity.roam_timer -= 1
        if entity.roam_timer <= 0:
            entity.roam_direction = random.uniform(0, math.tau)
            entity.roam_timer = (
                random.randint(25, 60)
                if entity.species == 'fish'
                else random.randint(90, 180)
            )

        roam_weight = 0.8
        if entity.species in ['rabbit', 'deer'] and hunger_ratio > 0.8 and thirst_ratio > 0.8:
            roam_weight = 1.5
        if entity.state in ["STARVING", "DEHYDRATED", "FLEEING"]:
            roam_weight = 0.25

        fx += math.cos(entity.roam_direction) * roam_weight
        fy += math.sin(entity.roam_direction) * roam_weight

        # Normalize force
        mag = math.hypot(fx, fy)
        if mag > 0:
            fx /= mag
            fy /= mag

        return fx, fy

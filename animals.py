import random
import math
import config
import world as world_mod
from ai import AnimalAI
from world import Burrow


def _place_bird_in_tree(bird, tree):
    angle = random.uniform(0, math.tau)
    distance = math.sqrt(random.random()) * max(0, tree.radius - bird.radius)
    bird.in_tree = tree
    bird.perch_position = (
        tree.x + math.cos(angle) * distance,
        tree.y + math.sin(angle) * distance,
    )
    bird.x, bird.y = bird.perch_position
    bird.is_hidden = True


def _feed_predator(predator, prey):
    meal_fraction = 1.0
    if predator.species == "hawk" or (
        predator.species == "wolf" and prey.species == "rabbit"
    ):
        meal_fraction = 0.5

    predator.hunger = min(
        predator.max_hunger,
        predator.hunger + predator.max_hunger * meal_fraction,
    )
    if predator.hunger >= predator.max_hunger * 0.9:
        predator.feeding_cooldown = config.PREDATOR_FULL_COOLDOWN


class Animal:
    def __init__(self, x, y, species, parents=None):
        self.tick_offset = random.randint(0, 5)
        self.tick_count = 0
        self.x = x
        self.y = y
        self.species = species
        self.parents = parents
        stats = config.ANIMAL_STATS[species]

        self.max_hunger = stats['max_hunger']
        self.hunger = self.max_hunger
        self.hunger_loss = stats['hunger_loss']

        self.max_health = stats['health']
        self.health = self.max_health

        self.base_speed = stats['speed']
        self.sprint_speed = stats['sprint_speed']
        self.speed = self.base_speed

        self.max_stamina = stats['stamina']
        self.stamina = self.max_stamina

        self.max_thirst = stats['max_thirst']
        self.thirst = self.max_thirst
        self.thirst_loss = stats['thirst_loss']
        self.water_speed = stats['water_speed']

        self.lifespan = stats['lifespan'] * random.uniform(0.8, 1.2)
        self.age = 0
        self.radius = stats['radius']

        self.gender = random.choice(["male", "female"])
        self.is_adult = False
        self.pregnant = False
        self.pregnancy_timer = 0

        self.dead = False
        self.ai = AnimalAI(species, parents)

        self.vx = 0.0
        self.vy = 0.0
        self.state = "FORAGING"
        self.roam_direction = random.uniform(0, math.tau)
        self.roam_timer = random.randint(90, 180)
        self.is_hidden = False
        self.current_activity = None
        self.activity_target = None
        self.activity_timer = 0
        self.feeding_cooldown = 0
        self.memory_share_timer = random.randint(0, 60)

    def mutate(self):
        # Evolution: Slight variations in stats from parents
        self.max_hunger *= random.uniform(0.95, 1.05)
        self.max_health *= random.uniform(0.95, 1.05)
        self.base_speed *= random.uniform(0.95, 1.05)
        self.sprint_speed *= random.uniform(0.95, 1.05)
        self.max_stamina *= random.uniform(0.95, 1.05)
        self.max_thirst *= random.uniform(0.95, 1.05)

        self.health = self.max_health
        self.hunger = self.max_hunger
        self.thirst = self.max_thirst
        self.stamina = self.max_stamina

    def update(self, world, animals):
        if self.dead: return
        if self.activity_timer > 0:
            self.activity_timer -= 1
        else:
            self.current_activity = None
            self.activity_target = None

        self.age += 1
        if self.age > self.lifespan * 0.2:
            self.is_adult = True

        # Old age penalty
        age_factor = 1.0
        if self.age > self.lifespan * 0.8:
            age_factor = 0.5 # Slow down when old

        if self.age > self.lifespan:
            self.die("age", world)
            return

        self.ai.decay_memory()
        self.tick_count += 1
        if self.feeding_cooldown > 0:
            self.feeding_cooldown -= 1

        # Swarm intelligence: share memory with nearby friends
        self.memory_share_timer -= 1
        if self.memory_share_timer <= 0:
            if getattr(self, 'is_adult', False):
                nearby = world.spatial_hash.get_nearby(self.x, self.y) if hasattr(world, 'spatial_hash') else animals
                for other in nearby:
                    if getattr(other, 'species', None) == self.species and other != self and not getattr(other, 'dead', True):
                        if (other.x - self.x)**2 + (other.y - self.y)**2 < 2500:
                            for key, mem in other.ai.memory_map.items():
                                if key not in self.ai.memory_map:
                                    self.ai.memory_map[key] = {'danger_day': 0.0, 'danger_night': 0.0, 'food': 0.0, 'water': 0.0}
                                self.ai.memory_map[key]['danger_day'] = max(self.ai.memory_map[key]['danger_day'], mem['danger_day'])
                                self.ai.memory_map[key]['danger_night'] = max(self.ai.memory_map[key]['danger_night'], mem['danger_night'])
                                self.ai.memory_map[key]['food'] = max(self.ai.memory_map[key]['food'], mem['food'])
                                self.ai.memory_map[key]['water'] = max(self.ai.memory_map[key]['water'], mem['water'])
            self.memory_share_timer = 60

        if getattr(self, 'is_hidden', False):
            self.hunger -= self.hunger_loss * 0.2
            self.thirst -= self.thirst_loss * 0.2
        else:
            self.hunger -= self.hunger_loss
            self.thirst -= self.thirst_loss

        if self.hunger <= 0 or self.thirst <= 0:
            self.health -= 0.1

        if self.health <= 0:
            if self.hunger <= 0 and self.thirst <= 0:
                cause = "hunger and thirst"
            elif self.hunger <= 0:
                cause = "hunger"
            else:
                cause = "thirst"
            self.die(cause, world)
            return

        # Health penalty speed
        health_factor = max(0.3, self.health / self.max_health)

        in_water = world.in_water(self.x, self.y)

        if in_water:
            if self.thirst < self.max_thirst:
                self.record_activity("drinking", self.x, self.y)
            self.thirst = min(self.max_thirst, self.thirst + 1.0)

        if in_water and self.species not in ['sparrow', 'hawk']:
            current_speed = self.water_speed
            if self.species == 'fish' and self.underwater:
                current_speed = config.FISH_UNDERWATER_SPEED
        elif self.species in ['sparrow', 'hawk']:
            current_speed = self.sprint_speed if self.flying else self.base_speed
            if self.species == 'hawk' and self.dive_target:
                current_speed = config.HAWK_DIVE_SPEED
        else:
            # Sprints if hungry, thirsty, or in danger (simulated by ai vector magnitude if we wanted, but let's just tie it to stamina)
            if self.stamina > 0:
                current_speed = self.sprint_speed * age_factor * health_factor
                self.stamina -= 0.5
            else:
                current_speed = self.base_speed * age_factor * health_factor

        if not in_water and self.stamina < self.max_stamina:
            self.stamina += 0.1

        # Movement (Tick staggering for heavy AI)
        if (
            self.tick_count % 6 == self.tick_offset
            or (self.species == 'hawk' and self.dive_target)
            or (self.species == 'fish' and self.underwater)
        ):
            fx, fy = self.ai.calculate_force(self, world, animals)
            self.vx = fx * current_speed
            self.vy = fy * current_speed
        else:
            speed_mag = math.hypot(self.vx, self.vy)
            if speed_mag > 0:
                self.vx = (self.vx / speed_mag) * current_speed
                self.vy = (self.vy / speed_mag) * current_speed
        self.x += self.vx
        self.y += self.vy

        movement_margin = self.radius
        self.x = max(movement_margin, min(config.SCREEN_WIDTH - movement_margin, self.x))
        self.y = max(movement_margin, min(config.SCREEN_HEIGHT - movement_margin, self.y))

        # FSM Update (Predator Check)
        predator_near = False
        for other in animals:
            is_predator = other.species == 'wolf' or (
                self.species == 'rabbit' and other.species == 'snake'
            )
            if is_predator and not other.dead and self.species in ['rabbit', 'deer']:
                if math.hypot(other.x - self.x, other.y - self.y) < 150:
                    predator_near = True
                    break

        # Predator check is now handled in ai.py via state overrides, but we leave the state setting here
        # or we remove predator_near. Wait, actually we can just keep predator_near, but ai.py can override it.
        # Actually, let's keep it here but let ai.py handle complex states. Wait, ai.py just uses state.
        # The prompt says: "In Rabbit.update, set self.is_hidden = True if the rabbit's state is "FLEEING", it has a home_burrow, and is within 10 pixels of it. Otherwise, set it to False."
        if predator_near:
            if self.state not in ["STARVING", "DEHYDRATED"]:
                self.state = "FLEEING"
            # Rabbit burrow reinforcement
            if self.species == 'rabbit' and hasattr(self, 'home_burrow') and self.home_burrow:
                if math.hypot(self.home_burrow.x - self.x, self.home_burrow.y - self.y) < 10:
                    self.ai.weights['burrow'] *= 1.05 # Reached burrow, positive reinforcement
        else:
            if self.state not in ["STARVING", "DEHYDRATED", "AGGRESSIVE"]:
                self.state = "FORAGING"

        self.eat(world)
        self.reproduce(world, animals)

    def die(self, cause, world):
        if self.dead:
            return

        self.dead = True
        print(f"{self.species} died to {cause}")
        world.carcasses.append(world_mod.Carcass(self.x, self.y, self.species))

    def record_activity(self, activity, x, y):
        self.current_activity = activity
        self.activity_target = (x, y)
        self.activity_timer = 120

    def eat(self, world):
        pass # overridden by subclasses

    def reproduce(self, world, animals):
        pass # overridden by subclasses


class Rabbit(Animal):
    def __init__(self, x, y, parents=None):
        super().__init__(x, y, 'rabbit', parents)
        self.home_burrow = None
        self.carried_food = 0
        self.daily_phase = "ROAMING"

    def update(self, world, animals):
        if not self.is_adult and world.season == "spring" and getattr(self, "home_burrow", None):
            self.thirst = self.max_thirst # Baby rabbits don't need to drink until summer
            # Keep them locked to the burrow radius
            if math.hypot(self.x - self.home_burrow.x, self.y - self.home_burrow.y) > self.home_burrow.radius * 2:
                self.x = self.home_burrow.x + random.uniform(-self.home_burrow.radius, self.home_burrow.radius)
                self.y = self.home_burrow.y + random.uniform(-self.home_burrow.radius, self.home_burrow.radius)

        super().update(world, animals)
        if self.dead: return

        if self.is_adult and self.home_burrow:
            if self.home_burrow.owner_male != self and self.home_burrow.owner_female != self:
                if self in self.home_burrow.occupants:
                    self.home_burrow.occupants.remove(self)
                self.home_burrow = None

        at_burrow = bool(
            self.home_burrow
            and math.hypot(self.x - self.home_burrow.x, self.y - self.home_burrow.y) < 20
        )
        self.is_hidden = self.state in ["FLEEING", "SLEEPING"] and at_burrow

        self._eat_from_burrow()

        if self.home_burrow is None:
            self.state = "SEARCHING"
            if self.gender == "female":
                for b in world.burrows:
                    if b.owner_female is None and b.owner_male is not None and not b.owner_male.dead:
                        if math.hypot(self.x - b.x, self.y - b.y) < 50:
                            self.home_burrow = b
                            b.owner_female = self
                            b.occupants.append(self)
                            break
            elif self.gender == "male":
                found = False
                for b in world.burrows:
                    if b.owner_male is None and b.owner_female is None:
                        if math.hypot(self.x - b.x, self.y - b.y) < 50:
                            self.home_burrow = b
                            b.owner_male = self
                            b.occupants.append(self)
                            found = True
                            break
                if not found and random.random() < 0.01 and self._is_good_burrow_site(world):
                    b = world_mod.Burrow(self.x, self.y)
                    world.burrows.append(b)
                    self.home_burrow = b
                    b.owner_male = self
                    b.occupants.append(self)
        else:
            if self.carried_food > 0:
                if math.hypot(self.x - self.home_burrow.x, self.y - self.home_burrow.y) < 20:
                    available_space = max(
                        0,
                        config.BURROW_MAX_FOOD - self.home_burrow.food_stored,
                    )
                    stored_food = min(self.carried_food, available_space)
                    self.home_burrow.food_stored += stored_food
                    self.carried_food -= stored_food
                    if self.home_burrow.food_stored >= config.BURROW_MAX_FOOD:
                        self.carried_food = 0

            # Only assign non-emergency states if not already starving/dehydrated/fleeing
            if self.state not in ["STARVING", "DEHYDRATED", "FLEEING"]:
                # Check if we need to feed babies in spring
                has_babies = any(
                    occupant for occupant in self.home_burrow.occupants
                    if occupant.species == 'rabbit' and not occupant.is_adult and getattr(occupant, 'parents', None) and self in occupant.parents
                )

                if (world.season in ["fall", "winter"] or self.home_burrow.food_stored < config.BURROW_MAX_FOOD) or (world.season == "spring" and has_babies):
                    self.state = "FORAGING"
                else:
                    block = int((world.season_tick % config.DAY_LENGTH) // (config.DAY_LENGTH / 4))
                    mem = getattr(self, 'ai', None)
                    if mem is not None:
                        mem = mem.get_location_memory(self.x, self.y)
                    else:
                        mem = {}
                    max_danger_block = 3 if mem.get('danger_night', 0) > mem.get('danger_day', 0) else 1

                    if block == max_danger_block:
                        self.state = "SLEEPING"
                    elif block % 2 == 0:
                        self.state = "ROAMING"
                    else:
                        self.state = "SOCIALIZING"

    def _is_good_burrow_site(self, world):
        if world.in_water(self.x, self.y):
            return False

        has_food_nearby = any(
            bush.food_count > 0
            and math.hypot(self.x - bush.x, self.y - bush.y) <= 250
            for bush in world.bushes
        )
        if not has_food_nearby:
            return False

        river = world.river
        if self.y < river.y:
            water_distance = river.y - self.y
        elif self.y > river.y + river.h:
            water_distance = self.y - (river.y + river.h)
        else:
            water_distance = 0

        for water_hole in world.water_holes:
            if water_hole.frozen:
                continue
            dx = max(abs(self.x - water_hole.x) - water_hole.w / 2, 0)
            dy = max(abs(self.y - water_hole.y) - water_hole.h / 2, 0)
            water_distance = min(water_distance, math.hypot(dx, dy))

        return water_distance <= 250

    def eat(self, world):
        # Rabbits eat bushes
        for bush in world.bushes:
            can_store_food = (
                self.home_burrow
                and self.carried_food < 5
                and self.home_burrow.food_stored + self.carried_food < config.BURROW_MAX_FOOD
            )
            if (
                bush.food_count > 0
                and (self.hunger < self.max_hunger or can_store_food)
                and math.hypot(self.x - bush.x, self.y - bush.y) < bush.radius + self.radius
                and not self.is_hidden
            ):
                nut = bush.eat()
                if self.hunger < self.max_hunger:
                    self.hunger += nut
                elif can_store_food:
                    # Carry food
                    self.carried_food += 1

                # Seed dropping (20% chance)
                if random.random() < config.BUSH_SEED_DROP_CHANCE:
                    world.seeds.append(("bush", self.x, self.y))
                self.record_activity("eating", bush.x, bush.y)
                break

    def _eat_from_burrow(self):
        if (
            self.home_burrow
            and self.home_burrow.food_stored > 0
            and self.hunger < self.max_hunger
            and math.hypot(self.x - self.home_burrow.x, self.y - self.home_burrow.y) < 20
        ):
            self.home_burrow.food_stored -= 1
            self.hunger += config.BERRY_NUTRIENT
            self.record_activity("eating", self.home_burrow.x, self.home_burrow.y)

    def reproduce(self, world, animals):
        # Winter reproduction in burrow
        if world.season == "winter" and self.gender == "female" and self.home_burrow and not self.pregnant:
            # Find a male mate in the burrow
            male_mate = None
            for occupant in self.home_burrow.occupants:
                if occupant.gender == "male" and occupant.is_adult:
                    male_mate = occupant
                    break

            if male_mate:
                self.mate = male_mate
                self.pregnant = True

        if self.pregnant and world.season == "spring":
            self.pregnant = False
            num_kids = random.randint(2, 3)
            for _ in range(num_kids):
                parents = [self, getattr(self, 'mate', None)]
                kid = Rabbit(
                    self.home_burrow.x + random.uniform(-self.home_burrow.radius, self.home_burrow.radius),
                    self.home_burrow.y + random.uniform(-self.home_burrow.radius, self.home_burrow.radius),
                    parents=parents,
                )
                kid.mutate()
                kid.home_burrow = self.home_burrow
                self.home_burrow.occupants.append(kid)
                animals.append(kid)

class Deer(Animal):
    def __init__(self, x, y, parents=None):
        super().__init__(x, y, 'deer', parents)
        self.mate = None
        self.boredom = 0
        self.wanderlust_weight = 0.0

    def update(self, world, animals):
        super().update(world, animals)
        if self.dead:
            return

        if self.hunger > self.max_hunger * 0.7 and self.thirst > self.max_thirst * 0.7:
            self.boredom += 1
        else:
            self.boredom = 0

        if self.boredom > 600: # 10 seconds of being full in one spot
            self.wanderlust_weight = min(2.0, self.wanderlust_weight + 0.01)

    def eat(self, world):
        # Deer eat bushes and trees
        if self.hunger >= self.max_hunger:
            return

        eaten = False
        for tree in world.trees:
            if tree.food_count > 0 and math.hypot(self.x - tree.x, self.y - tree.y) < tree.radius + self.radius:
                nut = tree.eat()
                self.hunger += nut
                self.record_activity("eating", tree.x, tree.y)
                eaten = True
                break

        if not eaten:
            for bush in world.bushes:
                if bush.food_count > 0 and math.hypot(self.x - bush.x, self.y - bush.y) < bush.radius + self.radius:
                    nut = bush.eat()
                    self.hunger += nut
                    if random.random() < config.BUSH_SEED_DROP_CHANCE:
                        world.seeds.append(("bush", self.x, self.y))
                    self.record_activity("eating", bush.x, bush.y)
                    break

    def reproduce(self, world, animals):
        if world.season == "fall" and self.gender == "female" and self.is_adult and not self.pregnant:
            for a in animals:
                if a.species == 'deer' and a.gender == 'male' and a.is_adult:
                    if math.hypot(self.x - a.x, self.y - a.y) < 30:
                        self.mate = a
                        a.mate = self
                        self.pregnant = True
                        break

        if self.pregnant and world.season == "spring":
            self.pregnant = False
            kid = Deer(self.x, self.y, parents=[self, self.mate])
            kid.mutate()
            animals.append(kid)

class Wolf(Animal):
    def __init__(self, x, y, parents=None):
        super().__init__(x, y, 'wolf', parents)
        self.damage = config.ANIMAL_STATS['wolf']['damage']
        self.mate = None
        self.attack_cooldown = 0
        self.chase_target = None
        self.chase_timer = 0
        self.wander_timer = 0
        self.ignored_prey = {}

    def update(self, world, animals):
        super().update(world, animals)
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        if self.wander_timer > 0:
            self.wander_timer -= 1

        keys_to_delete = []
        for prey, timer in self.ignored_prey.items():
            self.ignored_prey[prey] -= 1
            if self.ignored_prey[prey] <= 0:
                keys_to_delete.append(prey)
        for prey in keys_to_delete:
            del self.ignored_prey[prey]

    def eat(self, world):
        if self.hunger >= self.max_hunger:
            return
        for carcass in world.carcasses:
            if (self.x - carcass.x)**2 + (self.y - carcass.y)**2 < (carcass.radius + self.radius)**2:
                amount_needed = self.max_hunger - self.hunger
                nutrients = carcass.eat(amount_needed)
                self.hunger += nutrients
                self.record_activity("eating", carcass.x, carcass.y)
                break

    def reproduce(self, world, animals):
        if world.season == "fall" and self.gender == "female" and self.is_adult and not self.pregnant:
            for a in animals:
                if a.species == 'wolf' and a.gender == 'male' and a.is_adult:
                    if math.hypot(self.x - a.x, self.y - a.y) < 30:
                        self.mate = a
                        a.mate = self
                        self.pregnant = True
                        break

        if self.pregnant and world.season == "spring":
            self.pregnant = False
            kid = Wolf(self.x, self.y, parents=[self, self.mate])
            kid.mutate()
            animals.append(kid)

    def hunt(self, animals, world):
        if self.hunger >= self.max_hunger * 0.9 or self.feeding_cooldown > 0:
            return
        if self.attack_cooldown <= 0:
            for a in animals:
                if getattr(a, 'is_hidden', False):
                    continue
                if a.species in ['rabbit', 'deer'] and not a.dead:
                    if math.hypot(self.x - a.x, self.y - a.y) < self.radius + a.radius + 5:
                        a.health -= self.damage
                        self.attack_cooldown = 30 # 0.5 sec cooldown

                        if a.health <= 0:
                            a.die("wolf", world)
                            if a.species == 'rabbit':
                                self.ai.weights['hunt_rabbit'] = min(3.0, self.ai.weights.get('hunt_rabbit', 1.0) + 0.1)
                            elif a.species == 'deer':
                                self.ai.weights['hunt_deer'] = min(3.0, self.ai.weights.get('hunt_deer', 1.0) + 0.1)
                            _feed_predator(self, a)
                            self.attack_cooldown = (
                                1000 if self.feeding_cooldown > 0 else 30
                            )

                            # Negative reinforcement for prey species in this area
                            a.ai.update_memory(a.x, a.y, 5, 'danger', is_night=getattr(world, 'season_tick', 0) > __import__('config').DAY_LENGTH)
                            # Positive reinforcement for wolf
                            self.ai.update_memory(self.x, self.y, 5, 'food')
                        break

class Fish(Animal):
    def __init__(self, x, y, parents=None):
        super().__init__(x, y, 'fish', parents)
        self.hunger_loss = 0
        self.thirst_loss = 0
        self.age = 0
        self.underwater = False
        self.underwater_timer = 0
        self.dive_cooldown = 0

    def update(self, world, animals):
        if self.dead: return

        if self.underwater:
            self.underwater_timer -= 1
            if self.underwater_timer <= 0:
                self.underwater = False
                self.underwater_timer = 0
                self.dive_cooldown = config.FISH_DIVE_COOLDOWN
        elif self.dive_cooldown > 0:
            self.dive_cooldown -= 1
        elif any(
            not animal.dead
            and animal.species in ['hawk', 'snake']
            and math.hypot(animal.x - self.x, animal.y - self.y) < 140
            for animal in animals
            if animal is not self
        ):
            self.underwater = True
            self.underwater_timer = config.FISH_DIVE_DURATION

        self.is_hidden = self.underwater
        super().update(world, animals)
        if self.dead:
            return

    def eat(self, world):
        pass

    def reproduce(self, world, animals):
        if world.season == "spring":
            if self.gender == "female" and self.is_adult and not self.pregnant:
                if random.random() < 0.05:
                    num_eggs = random.randint(2, 4)
                    for _ in range(num_eggs):
                        world.eggs.append(world_mod.Egg(self.x, self.y, 'fish', [self]))
                    self.pregnant = True
            elif self.gender == "male" and self.is_adult:
                for egg in world.eggs:
                    if egg.species == 'fish' and not egg.dead and len(egg.parents) == 1:
                        if (self.x - egg.x)**2 + (self.y - egg.y)**2 < 400:
                            egg.parents.append(self)
                            break

class Snake(Animal):
    def __init__(self, x, y, parents=None):
        super().__init__(x, y, 'snake', parents)
        self.damage = config.ANIMAL_STATS['snake']['damage']
        self.attack_cooldown = 0
        self.climbing_tree = None
        self.tree_camp_timer = 0

    def update(self, world, animals):
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        if self.climbing_tree and (self.climbing_tree.dead or self.state == "FLEEING"):
            self.climbing_tree = None

        if self.climbing_tree:
            self.tree_camp_timer -= 1
            if self.tree_camp_timer <= 0:
                self.climbing_tree = None
            else:
                self.x = self.climbing_tree.x
                self.y = self.climbing_tree.y
                self.vx = 0
                self.vy = 0
                # Wait for prey or eggs

        super().update(world, animals)

        if self.dead: return

        # Decide to climb tree if hungry and near one
        if not self.climbing_tree and self.hunger < self.max_hunger * 0.8:
            nearby = world.spatial_hash.get_nearby(self.x, self.y) if hasattr(world, 'spatial_hash') else world.trees
            for plant in nearby:
                if isinstance(plant, world_mod.Tree):
                    if (self.x - plant.x)**2 + (self.y - plant.y)**2 < (plant.radius + self.radius)**2:
                        if random.random() < 0.05:
                            self.climbing_tree = plant
                            self.tree_camp_timer = 600
                        break

    def eat(self, world):
        if self.hunger >= self.max_hunger: return
        # Can eat eggs directly from tree
        if self.climbing_tree:
            for egg in world.eggs:
                if egg.x == self.climbing_tree.x and egg.y == self.climbing_tree.y:
                    egg.dead = True
                    self.hunger = min(self.max_hunger, self.hunger + 100)
                    self.record_activity("eating_egg", egg.x, egg.y)
                    return

        # Eat carcass
        for carcass in world.carcasses:
            if carcass.species in ['fish', 'rabbit', 'sparrow']:
                if (self.x - carcass.x)**2 + (self.y - carcass.y)**2 < (carcass.radius + self.radius)**2:
                    nutrients = carcass.eat(self.max_hunger - self.hunger)
                    self.hunger += nutrients
                    self.record_activity("eating_carcass", carcass.x, carcass.y)
                    return

    def hunt(self, animals, world):
        if self.hunger >= self.max_hunger * 0.9 or self.feeding_cooldown > 0:
            return
        if self.attack_cooldown <= 0:
            for a in animals:
                submerged_prey = (
                    self.species == 'snake'
                    and a.species == 'fish'
                    and getattr(a, 'underwater', False)
                )
                if getattr(a, 'is_hidden', False) and not submerged_prey and not (
                    getattr(a, 'in_tree', None)
                    and self.climbing_tree is a.in_tree
                ):
                    continue
                if a.species in ['rabbit', 'fish', 'sparrow'] and not a.dead:
                    if a.species == 'sparrow' and a.flying:
                        continue
                    # If in tree, can only attack birds that land, or baby rabbits at roots, just use distance
                    # Birds landing is implicitly being at ground level or tree x,y
                    if (self.x - a.x)**2 + (self.y - a.y)**2 < (self.radius + a.radius + 10)**2:
                        a.health -= self.damage
                        self.attack_cooldown = 20
                        if a.health <= 0:
                            a.die("snake", world)
                            _feed_predator(self, a)
                            self.attack_cooldown = 300
                        break

    def reproduce(self, world, animals):
        if world.season == "spring" and self.gender == "female" and self.is_adult and not self.pregnant:
            nearby = world.spatial_hash.get_nearby(self.x, self.y) if hasattr(world, 'spatial_hash') else animals
            for a in nearby:
                if getattr(a, 'species', None) == 'snake' and getattr(a, 'gender', None) == 'male' and getattr(a, 'is_adult', False):
                    if (self.x - a.x)**2 + (self.y - a.y)**2 < 900:
                        world.eggs.append(world_mod.Egg(self.x, self.y, 'snake', [self, a]))
                        self.pregnant = True
                        break

class Sparrow(Animal):
    def __init__(self, x, y, parents=None, start_flying=True):
        super().__init__(x, y, 'sparrow', parents)
        self.flying = start_flying
        self.in_tree = None
        self.home_nest = None
        self.flight_timer = 0
        self.flight_target = None
        self.flight_goal = None
        self.ground_target = None
        self.landing_cooldown = 0
        self.perch_position = None
        self.nest_search_timer = random.randint(300, 600)

        if parents and getattr(parents[0], 'home_nest', None):
            self.flying = False
            self.in_tree = parents[0].home_nest.tree
            self.x, self.y = self.in_tree.x, self.in_tree.y

    def _nearest_tree(self, world):
        trees = [
            tree for tree in world.trees
            if not tree.dead
            and 150 <= tree.x <= config.SCREEN_WIDTH - 150
            and 150 <= tree.y <= config.SCREEN_HEIGHT - 150
        ]
        alternatives = [tree for tree in trees if tree is not self.in_tree]
        return min(
            alternatives or trees,
            key=lambda tree: math.hypot(tree.x - self.x, tree.y - self.y),
            default=None,
        )

    def _water_target(self, world):
        river = world.river
        targets = [
            (min(max(self.x, 30), config.SCREEN_WIDTH - 30), river.y + river.h / 2)
        ]
        targets.extend(
            (hole.x, hole.y)
            for hole in world.water_holes
            if not hole.frozen
        )
        return min(targets, key=lambda target: math.hypot(target[0] - self.x, target[1] - self.y))

    def _choose_flight_goal(self, world, goal):
        self.flight_goal = goal
        self.ground_target = None
        if goal == "tree":
            nest_tree = (
                self.home_nest.tree
                if self.home_nest and not self.home_nest.tree.dead
                else None
            )
            tree = nest_tree or self._nearest_tree(world)
            self.flight_target = (tree.x, tree.y) if tree else None
        elif goal == "food":
            bush = min(
                (bush for bush in world.bushes if not bush.dead and bush.food_count > 0),
                key=lambda bush: math.hypot(bush.x - self.x, bush.y - self.y),
                default=None,
            )
            self.flight_target = (bush.x, bush.y) if bush else None
        elif goal == "water":
            self.flight_target = self._water_target(world)

    def update(self, world, animals):
        if self.dead: return

        predators_near = any(
            other.species in ['hawk', 'snake', 'wolf']
            and not other.dead
            and not getattr(other, 'is_hidden', False)
            and math.hypot(other.x - self.x, other.y - self.y) < 180
            for other in animals
            if other is not self
        )

        if self.in_tree and self.in_tree.dead:
            self.in_tree = None
            self.perch_position = None
        if self.home_nest and self.home_nest.tree.dead:
            self.home_nest = None

        if self.landing_cooldown > 0:
            self.landing_cooldown -= 1
        if self.in_tree and not self.flying and self.perch_position:
            self.x, self.y = self.perch_position

        needs_food = self.hunger < self.max_hunger * 0.9
        needs_water = self.thirst < self.max_thirst * 0.8
        if self.flying:
            self.stamina = max(0, self.stamina - 0.5)
            self.flight_timer += 1
            goal = "tree" if predators_near else (
                "water" if needs_water else "food" if needs_food else "tree"
            )
            if self.flight_goal != goal or self.flight_target is None:
                self._choose_flight_goal(world, goal)

            if self.flight_goal == "tree" and self.flight_target:
                target_tree = next(
                    (
                        tree for tree in world.trees
                        if not tree.dead
                        and (tree.x, tree.y) == self.flight_target
                    ),
                    None,
                )
                arrived = target_tree and math.hypot(self.x - target_tree.x, self.y - target_tree.y) < target_tree.radius + 12
            elif self.flight_target:
                target_x, target_y = self.flight_target
                arrived = math.hypot(self.x - target_x, self.y - target_y) < 14
            else:
                arrived = False

            if arrived:
                self.flying = False
                self.flight_timer = 0
                self.landing_cooldown = config.BIRD_LANDING_COOLDOWN
                if self.flight_goal == "tree" and target_tree:
                    _place_bird_in_tree(self, target_tree)
                else:
                    self.in_tree = None
                    self.perch_position = None
                    self.ground_target = self.flight_target
                self.flight_target = None
            elif self.stamina <= 0 or self.flight_timer >= 240:
                self.flying = False
                self.flight_timer = 0
                self.landing_cooldown = config.BIRD_LANDING_COOLDOWN
                nearest_tree = self._nearest_tree(world)
                self.in_tree = None
                self.perch_position = None
                if nearest_tree and math.hypot(nearest_tree.x - self.x, nearest_tree.y - self.y) < 50:
                    _place_bird_in_tree(self, nearest_tree)
                self.ground_target = None
                self.flight_target = None
                self.flight_goal = "tree"
        else:
            self.stamina = min(self.max_stamina, self.stamina + 0.75)
            if self.nest_search_timer > 0:
                self.nest_search_timer -= 1
            at_food = self.flight_goal == "food" and any(
                bush.food_count > 0 and math.hypot(self.x - bush.x, self.y - bush.y) < bush.radius + self.radius
                for bush in world.bushes
            )
            at_water = world.in_water(self.x, self.y)
            if (
                self.in_tree
                and not self.home_nest
                and self.hunger >= self.max_hunger * 0.9
                and self.thirst >= self.max_thirst * 0.8
                and self.landing_cooldown == 0
                and self.nest_search_timer == 0
            ):
                candidates = [
                    tree for tree in world.trees
                    if not tree.dead and tree is not self.in_tree
                ]
                target_tree = random.choice(candidates) if candidates else None
                self.nest_search_timer = random.randint(300, 600)
                if target_tree:
                    self.flight_goal = "tree"
                    self.flight_target = (target_tree.x, target_tree.y)
                    self.flying = True
                    self.in_tree = None
                    self.perch_position = None
            elif self.landing_cooldown == 0 and predators_near:
                self._choose_flight_goal(world, "tree")
                self.flying = True
                self.in_tree = None
                self.perch_position = None
            elif self.landing_cooldown == 0:
                if needs_water and not at_water:
                    self._choose_flight_goal(world, "water")
                    self.flying = True
                    self.in_tree = None
                    self.perch_position = None
                elif needs_food and not at_food:
                    self._choose_flight_goal(world, "food")
                    self.flying = True
                    self.in_tree = None
                    self.perch_position = None
                elif (
                    not needs_food
                    and not needs_water
                    and (
                        self.flight_goal != "water"
                        or self.thirst >= self.max_thirst
                    )
                    and not self.in_tree
                ):
                    self._choose_flight_goal(world, "tree")
                    self.flying = True

        if not self.is_adult and world.season == "spring":
            self.thirst = self.max_thirst # Babies don't need water

        self.is_hidden = bool(self.in_tree and not self.flying)
        super().update(world, animals)
        if self.in_tree and not self.flying:
            self.x, self.y = self.perch_position
            self.vx = self.vy = 0
            self.is_hidden = True
        elif not self.flying and self.ground_target:
            self.x, self.y = self.ground_target
            self.vx = self.vy = 0
            if self.flight_goal == "water" and self.thirst >= self.max_thirst:
                self.ground_target = None
            elif self.flight_goal == "food" and (
                self.hunger >= self.max_hunger
                or not any(bush.food_count > 0 for bush in world.bushes)
            ):
                self.ground_target = None

    def eat(self, world):
        if self.flying or self.in_tree or self.flight_goal != "food": return
        if self.hunger >= self.max_hunger: return

        nearby = world.spatial_hash.get_nearby(self.x, self.y) if hasattr(world, 'spatial_hash') else world.bushes
        for bush in nearby:
            if not isinstance(bush, world_mod.Bush): continue
            if bush.food_count > 0 and (self.x - bush.x)**2 + (self.y - bush.y)**2 < (bush.radius + self.radius)**2:
                nut = bush.eat()
                self.hunger += nut
                if random.random() < config.BUSH_SEED_DROP_CHANCE:
                    world.seeds.append(("bush", self.x, self.y))
                self.record_activity("eating", bush.x, bush.y)
                break

    def reproduce(self, world, animals):
        if not self.is_adult or not self.in_tree:
            return

        if self.gender == "male" and not self.home_nest and world.season == "spring":
            has_nest = any(n.tree == self.in_tree for n in world.nests)
            if not has_nest:
                nest = world_mod.Nest(self.in_tree)
                world.nests.append(nest)
                self.home_nest = nest
                nest.occupants.append(self)
        elif self.gender == "female" and not self.home_nest:
            for nest in world.nests:
                if (
                    nest.tree == self.in_tree
                    and len(nest.occupants) == 1
                    and nest.occupants[0].gender == 'male'
                ):
                    self.home_nest = nest
                    nest.occupants.append(self)
                    break

        if (
            self.gender == "female"
            and self.home_nest
            and self.in_tree is self.home_nest.tree
            and world.season == "spring"
            and not self.pregnant
        ):
            num_eggs = random.randint(2, 4)
            for _ in range(num_eggs):
                world.eggs.append(
                    world_mod.Egg(self.x, self.y, 'sparrow', self.home_nest.occupants.copy())
                )
            self.pregnant = True

class Hawk(Animal):
    def __init__(self, x, y, parents=None, start_flying=True):
        super().__init__(x, y, 'hawk', parents)
        self.flying = start_flying
        self.in_tree = None
        self.home_nest = None
        self.home_tree = None
        self.dive_target = None
        self.dive_timer = 0
        self.dive_cooldown = 0
        self.flight_timer = 0
        self.perch_timer = 0
        self.flight_target = None
        self.flight_goal = None
        self.ground_target = None
        self.landing_cooldown = 0
        self.perch_position = None
        self.damage = config.ANIMAL_STATS['hawk']['damage']
        self.attack_cooldown = 0

        if parents and getattr(parents[0], 'home_nest', None):
            self.flying = False
            self.in_tree = parents[0].home_nest.tree
            self.home_nest = parents[0].home_nest
            self.home_tree = self.in_tree
            self.x, self.y = self.in_tree.x, self.in_tree.y

    def _nearest_tree(self, world):
        return min(
            (
                tree for tree in world.trees
                if not tree.dead
                and 150 <= tree.x <= config.SCREEN_WIDTH - 150
                and 150 <= tree.y <= config.SCREEN_HEIGHT - 150
            ),
            key=lambda tree: math.hypot(tree.x - self.x, tree.y - self.y),
            default=None,
        )

    def _water_target(self, world):
        river = world.river
        targets = [
            (min(max(self.x, 30), config.SCREEN_WIDTH - 30), river.y + river.h / 2)
        ]
        targets.extend(
            (hole.x, hole.y)
            for hole in world.water_holes
            if not hole.frozen
        )
        return min(targets, key=lambda target: math.hypot(target[0] - self.x, target[1] - self.y))

    def update(self, world, animals):
        if self.dead: return

        if self.is_adult and self.home_nest and getattr(self, 'parents', None) and len(self.parents) > 0:
            if self in self.home_nest.occupants:
                self.home_nest.occupants.remove(self)
            self.home_nest = None
            self.home_tree = None

        if self.dive_cooldown > 0:
            self.dive_cooldown -= 1
        if self.landing_cooldown > 0:
            self.landing_cooldown -= 1
        if self.in_tree and self.in_tree.dead:
            self.in_tree = None
            self.perch_position = None
        if self.home_tree and self.home_tree.dead:
            self.home_tree = None
        if self.in_tree and not self.flying and self.perch_position:
            self.x, self.y = self.perch_position

        if self.dive_target:
            self.flying = True
            self.state = "DIVING"
            if getattr(self.dive_target, 'dead', True) or getattr(self.dive_target, 'is_hidden', False):
                self.dive_target = None
                self.dive_timer = 0
                self.dive_cooldown = config.HAWK_HUNT_COOLDOWN
                self.flying = False
                self.in_tree = None
                self.flight_timer = 0
                self.landing_cooldown = config.BIRD_LANDING_COOLDOWN
            else:
                self.stamina = max(0, self.stamina - 1.0)
                self.dive_timer += 1
                dx = self.dive_target.x - self.x
                dy = self.dive_target.y - self.y
                dist_sq = dx**2 + dy**2

                # Overshoot / Miss logic
                if dist_sq < (self.radius + self.dive_target.radius + 10)**2:
                    # Hit
                    self.dive_target.health -= self.damage
                    if self.dive_target.health <= 0:
                        self.dive_target.die("hawk", world)
                        _feed_predator(self, self.dive_target)
                    self.dive_target = None
                    self.dive_timer = 0
                    self.dive_cooldown = config.HAWK_HUNT_COOLDOWN
                    self.flying = False
                    self.in_tree = None
                    self.flight_timer = 0
                    self.landing_cooldown = config.BIRD_LANDING_COOLDOWN
                    nearest_tree = min(
                        (
                            tree for tree in world.trees
                            if 150 <= tree.x <= config.SCREEN_WIDTH - 150
                            and 150 <= tree.y <= config.SCREEN_HEIGHT - 150
                        ),
                        key=lambda tree: math.hypot(tree.x - self.x, tree.y - self.y),
                        default=None,
                    )
                    if nearest_tree and math.hypot(nearest_tree.x - self.x, nearest_tree.y - self.y) < 50:
                        _place_bird_in_tree(self, nearest_tree)
                        self.perch_timer = random.randint(180, 600)
                elif self.dive_timer >= config.HAWK_DIVE_DURATION:
                    # Missed / gave up
                    self.dive_target = None
                    self.dive_timer = 0
                    self.dive_cooldown = config.HAWK_HUNT_COOLDOWN
                    self.flying = False
                    self.in_tree = None
                    self.flight_timer = 0
                    self.landing_cooldown = config.BIRD_LANDING_COOLDOWN
        else:
            if self.flying:
                self.state = "PATROLLING"
                self.stamina = max(0, self.stamina - 0.2)
                self.flight_timer += 1
                needs_water = self.thirst < self.max_thirst * 0.8
                if needs_water and self.flight_goal != "water":
                    self.flight_goal = "water"
                    self.flight_target = self._water_target(world)
                    self.ground_target = None

                if self.state == "PATROLLING" and self.home_tree is not None and not needs_water:
                    self.ground_target = (
                        self.home_tree.x + 50 * math.cos(self.flight_timer * 0.1),
                        self.home_tree.y + 50 * math.sin(self.flight_timer * 0.1)
                    )

                if self.flight_goal == "water" and self.flight_target:
                    target_x, target_y = self.flight_target
                    reached_target = math.hypot(self.x - target_x, self.y - target_y) < 14
                    if reached_target or world.in_water(self.x, self.y):
                        self.flying = False
                        self.flight_target = None
                        self.ground_target = (
                            (target_x, target_y) if reached_target else (self.x, self.y)
                        )
                        self.flight_timer = 0
                        self.landing_cooldown = config.BIRD_LANDING_COOLDOWN
                elif self.flight_goal == "tree" and self.flight_target:
                    target_tree = next(
                        (
                            tree for tree in world.trees
                            if not tree.dead
                            and (tree.x, tree.y) == self.flight_target
                        ),
                        None,
                    )
                    if target_tree and math.hypot(self.x - target_tree.x, self.y - target_tree.y) < target_tree.radius + 12:
                        self.flying = False
                        _place_bird_in_tree(self, target_tree)
                        self.flight_target = None
                        self.flight_timer = 0
                        self.landing_cooldown = config.BIRD_LANDING_COOLDOWN
                        self.perch_timer = random.randint(180, 600)
                if self.flying and (self.stamina <= 0 or self.flight_timer >= 360):
                    self.flying = False
                    self.flight_timer = 0
                    self.landing_cooldown = config.BIRD_LANDING_COOLDOWN
                    self.flight_goal = "tree"
                    self.ground_target = None
                    nearest_tree = self._nearest_tree(world)
                    if nearest_tree and math.hypot(nearest_tree.x - self.x, nearest_tree.y - self.y) < 50:
                        _place_bird_in_tree(self, nearest_tree)
                        self.perch_timer = random.randint(180, 600)
            else:
                self.state = "PERCHED" if self.in_tree else "RESTING"
                self.stamina = min(self.max_stamina, self.stamina + 0.75)
                needs_food = self.hunger < self.max_hunger * 0.9
                needs_water = self.thirst < self.max_thirst * 0.8
                at_water = world.in_water(self.x, self.y)
                if self.landing_cooldown == 0 and needs_water and not at_water:
                    self.flying = True
                    self.in_tree = None
                    self.flight_goal = "water"
                    self.flight_target = self._water_target(world)
                    self.ground_target = None
                elif self.landing_cooldown == 0 and needs_food:
                    self.flying = True
                    self.in_tree = None
                    self.flight_goal = None
                    self.flight_target = None
                    self.ground_target = None
                elif (
                    self.landing_cooldown == 0
                    and self.thirst >= self.max_thirst
                    and not needs_food
                    and at_water
                ):
                    tree = self._nearest_tree(world)
                    self.flying = True
                    self.in_tree = None
                    self.flight_goal = "tree"
                    self.flight_target = (tree.x, tree.y) if tree else None
                    self.ground_target = None
                elif self.in_tree:
                    self.perch_timer = max(0, self.perch_timer - 1)
                    if self.landing_cooldown == 0 and self.perch_timer == 0 and self.stamina >= self.max_stamina * 0.8:
                        self.flying = True
                        self.in_tree = None
                        self.flight_goal = None
                        self.flight_target = None
                elif self.landing_cooldown == 0 and self.stamina >= self.max_stamina * 0.8 and random.random() < 0.02:
                    self.flying = True
                    self.flight_goal = None
                    self.flight_target = None

        self.is_hidden = bool(self.in_tree and not self.flying)
        if self.in_tree and not self.flying:
            self.x, self.y = self.perch_position
            self.vx = self.vy = 0

        super().update(world, animals)
        if self.in_tree and not self.flying:
            self.x, self.y = self.perch_position
            self.vx = self.vy = 0
            self.is_hidden = True
        elif not self.flying and self.ground_target:
            self.x, self.y = self.ground_target
            self.vx = self.vy = 0
            if self.flight_goal == "water" and self.thirst >= self.max_thirst:
                self.ground_target = None
                self.flight_goal = "tree"

    def eat(self, world):
        if self.flying: return
        if self.hunger >= self.max_hunger: return

        # Eat carcass
        for carcass in world.carcasses:
            if (self.x - carcass.x)**2 + (self.y - carcass.y)**2 < (carcass.radius + self.radius)**2:
                nutrients = carcass.eat(self.max_hunger - self.hunger)
                self.hunger += nutrients
                self.record_activity("eating_carcass", carcass.x, carcass.y)
                break

    def hunt(self, animals, world):
        if (
            self.hunger >= self.max_hunger * 0.9
            or self.feeding_cooldown > 0
        ):
            return
        if not self.flying:
            if self.in_tree and self.attack_cooldown <= 0:
                for prey in animals:
                    if (
                        prey.species == 'sparrow'
                        and not prey.dead
                        and getattr(prey, 'in_tree', None) is self.in_tree
                    ):
                        prey.health -= self.damage
                        if prey.health <= 0:
                            prey.die("hawk", world)
                            _feed_predator(self, prey)
                        self.attack_cooldown = 30
                        break
            return
        if self.dive_target or self.dive_cooldown > 0: return

        # Look for prey from high up (huge vision radius)
        best_target = None
        best_dist_sq = float('inf')
        for a in animals:
            same_tree = bool(self.in_tree and getattr(a, 'in_tree', None) is self.in_tree)
            if (
                a.species in ['sparrow', 'fish']
                and not getattr(a, 'dead', True)
                and (not getattr(a, 'is_hidden', False) or same_tree)
            ):
                # Don't target birds in trees unless we are in the same tree (handled by normal eating, wait Hawks eat meat)
                if getattr(a, 'in_tree', None) and not same_tree: continue
                if getattr(a, 'climbing_tree', None): continue

                d_sq = (a.x - self.x)**2 + (a.y - self.y)**2
                hunt_range = config.HAWK_SPARROW_DETECTION_RANGE if a.species == 'sparrow' else 400
                if d_sq < hunt_range**2:
                    if d_sq < best_dist_sq:
                        best_dist_sq = d_sq
                        best_target = a

        if best_target:
            self.dive_target = best_target
            self.dive_timer = 0

    def reproduce(self, world, animals):
        if world.season == "spring" and self.is_adult:
            if self.gender == "male" and not self.home_nest and self.in_tree:
                if self.home_tree is None:
                    self.home_tree = self.in_tree
                has_nest = any(n.tree == self.in_tree for n in world.nests)
                if not has_nest:
                    nest = world_mod.Nest(self.in_tree)
                    world.nests.append(nest)
                    self.home_nest = nest
                    nest.occupants.append(self)

            elif self.gender == "female" and not self.pregnant:
                for nest in world.nests:
                    if len(nest.occupants) == 1 and nest.occupants[0].gender == 'male':
                        self.home_nest = nest
                        self.home_tree = nest.tree
                        nest.occupants.append(self)
                        num_eggs = random.randint(1, 2)
                        for _ in range(num_eggs):
                            world.eggs.append(world_mod.Egg(self.x, self.y, 'hawk', nest.occupants.copy()))
                        self.pregnant = True
                        break

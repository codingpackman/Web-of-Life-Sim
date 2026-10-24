import random
import math
import config
from ai import AnimalAI
from world import Burrow

class Animal:
    def __init__(self, x, y, species, parents=None):
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
            self.die("age")
            return

        self.ai.decay_memory()

        # Swarm intelligence: share memory with nearby friends
        for other in animals:
            if other != self and other.species == self.species and not other.dead:
                dist = math.hypot(other.x - self.x, other.y - self.y)
                if dist < 50:
                    for key, mem in other.ai.memory_map.items():
                        if key not in self.ai.memory_map:
                            self.ai.memory_map[key] = {'danger': 0.0, 'food': 0.0, 'water': 0.0}
                        self.ai.memory_map[key]['danger'] = max(self.ai.memory_map[key]['danger'], mem['danger'])
                        self.ai.memory_map[key]['food'] = max(self.ai.memory_map[key]['food'], mem['food'])
                        self.ai.memory_map[key]['water'] = max(self.ai.memory_map[key]['water'], mem['water'])

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
            self.die(cause)
            return

        # Health penalty speed
        health_factor = max(0.3, self.health / self.max_health)

        in_water = world.in_water(self.x, self.y)

        if in_water:
            if self.thirst < self.max_thirst:
                self.record_activity("drinking", self.x, self.y)
            self.thirst = min(self.max_thirst, self.thirst + 1.0)
            current_speed = self.water_speed
        else:
            # Sprints if hungry, thirsty, or in danger (simulated by ai vector magnitude if we wanted, but let's just tie it to stamina)
            if self.stamina > 0:
                current_speed = self.sprint_speed * age_factor * health_factor
                self.stamina -= 0.5
            else:
                current_speed = self.base_speed * age_factor * health_factor

        if not in_water and self.stamina < self.max_stamina:
            self.stamina += 0.1

        # Movement
        fx, fy = self.ai.calculate_force(self, world, animals)
        self.vx = fx * current_speed
        self.vy = fy * current_speed
        self.x += self.vx
        self.y += self.vy

        self.x = max(self.radius, min(config.SCREEN_WIDTH - self.radius, self.x))
        self.y = max(self.radius, min(config.SCREEN_HEIGHT - self.radius, self.y))

        # FSM Update (Predator Check)
        predator_near = False
        for other in animals:
            if other.species == 'wolf' and not other.dead and self.species in ['rabbit', 'deer']:
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

    def die(self, cause):
        if self.dead:
            return

        self.dead = True
        print(f"{self.species} died to {cause}")

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

    def update(self, world, animals):
        if not self.is_adult and world.season == "spring" and getattr(self, "home_burrow", None):
            self.thirst = self.max_thirst # Baby rabbits don't need to drink until summer
            # Keep them locked to the burrow radius
            if math.hypot(self.x - self.home_burrow.x, self.y - self.home_burrow.y) > self.home_burrow.radius * 2:
                self.x = self.home_burrow.x + random.uniform(-self.home_burrow.radius, self.home_burrow.radius)
                self.y = self.home_burrow.y + random.uniform(-self.home_burrow.radius, self.home_burrow.radius)

        super().update(world, animals)
        if self.dead: return

        if self.hunger >= self.max_hunger and self.state != "FLEEING":
            self.state = "HOARDING"

        at_burrow = bool(
            self.home_burrow
            and math.hypot(self.x - self.home_burrow.x, self.y - self.home_burrow.y) < 20
        )
        self.is_hidden = self.state == "FLEEING" and at_burrow

        self._eat_from_burrow()

        # Deposit food in burrow during update phase to ensure it's captured
        if self.home_burrow and self.carried_food > 0:
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
                if self.hunger < self.max_hunger:
                    self.state = "FORAGING"

        # Dig burrow if male adult and no home
        if self.gender == "male" and self.is_adult and not self.home_burrow:
            if random.random() < 0.01 and self._is_good_burrow_site(world):
                b = Burrow(self.x, self.y)
                world.burrows.append(b)
                self.home_burrow = b
                b.occupants.append(self)

        # Find burrow if female
        if self.gender == "female" and self.is_adult and not self.home_burrow:
            for b in world.burrows:
                adult_occupants = sum(1 for o in b.occupants if o.is_adult and not o.dead)
                if adult_occupants < 2 and any(o.gender == "male" for o in b.occupants):
                    if math.hypot(self.x - b.x, self.y - b.y) < 50:
                        self.home_burrow = b
                        b.occupants.append(self)
                        break

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
            num_kids = random.randint(2, 5)
            for _ in range(num_kids):
                parents = [self, getattr(self, 'mate', None)]
                kid = Rabbit(self.home_burrow.x, self.home_burrow.y, parents=parents)
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
        pass # Wolf eating is handled in hunting logic (below)

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

    def hunt(self, animals):
        if self.attack_cooldown <= 0:
            for a in animals:
                if getattr(a, 'is_hidden', False):
                    continue
                if a.species in ['rabbit', 'deer'] and not a.dead:
                    if math.hypot(self.x - a.x, self.y - a.y) < self.radius + a.radius + 5:
                        a.health -= self.damage
                        self.attack_cooldown = 30 # 0.5 sec cooldown

                        if a.health <= 0:
                            a.die("wolf")
                            self.hunger = self.max_hunger # Restore hunger upon killing
                            self.attack_cooldown = 1000 # Stop hunting for a while

                            # Negative reinforcement for prey species in this area
                            a.ai.update_memory(a.x, a.y, 5, 'danger')
                            # Positive reinforcement for wolf
                            self.ai.update_memory(self.x, self.y, 5, 'food')
                        break

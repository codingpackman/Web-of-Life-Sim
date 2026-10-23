import random
import math
import config
from ai import AnimalAI
from world import Burrow

class Animal:
    def __init__(self, x, y, species):
        self.x = x
        self.y = y
        self.species = species
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

        self.lifespan = stats['lifespan']
        self.age = 0
        self.radius = stats['radius']

        self.gender = random.choice(["male", "female"])
        self.is_adult = False
        self.pregnant = False
        self.pregnancy_timer = 0

        self.dead = False
        self.ai = AnimalAI(species)

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

        self.age += 1
        if self.age > self.lifespan * 0.2:
            self.is_adult = True

        # Old age penalty
        age_factor = 1.0
        if self.age > self.lifespan * 0.8:
            age_factor = 0.5 # Slow down when old

        if self.age > self.lifespan:
            self.die()

        self.hunger -= self.hunger_loss
        self.thirst -= self.thirst_loss

        if self.hunger <= 0 or self.thirst <= 0:
            self.health -= 0.1

        if self.health <= 0:
            self.die()

        # Health penalty speed
        health_factor = max(0.3, self.health / self.max_health)

        in_water = world.in_water(self.x, self.y)

        if in_water:
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
        self.x += fx * current_speed
        self.y += fy * current_speed

        # Bounds checking
        self.x = max(0, min(config.SCREEN_WIDTH, self.x))
        self.y = max(0, min(config.SCREEN_HEIGHT, self.y))

        self.eat(world)
        self.reproduce(world, animals)

    def die(self):
        self.dead = True

    def eat(self, world):
        pass # overridden by subclasses

    def reproduce(self, world, animals):
        pass # overridden by subclasses


class Rabbit(Animal):
    def __init__(self, x, y):
        super().__init__(x, y, 'rabbit')
        self.home_burrow = None
        self.carried_food = 0

    def update(self, world, animals):
        super().update(world, animals)
        if self.dead: return

        # Dig burrow if male adult and no home
        if self.gender == "male" and self.is_adult and not self.home_burrow:
            if random.random() < 0.01: # Small chance per tick
                b = Burrow(self.x, self.y)
                world.burrows.append(b)
                self.home_burrow = b
                b.occupants.append(self)

        # Find burrow if female
        if self.gender == "female" and self.is_adult and not self.home_burrow:
            for b in world.burrows:
                if len(b.occupants) < 2 and any(o.gender == "male" for o in b.occupants):
                    if math.hypot(self.x - b.x, self.y - b.y) < 50:
                        self.home_burrow = b
                        b.occupants.append(self)
                        break

    def eat(self, world):
        # Rabbits eat bushes
        for bush in world.bushes:
            if bush.food_count > 0 and math.hypot(self.x - bush.x, self.y - bush.y) < bush.radius + self.radius:
                nut = bush.eat()
                if self.hunger < self.max_hunger:
                    self.hunger = min(self.max_hunger, self.hunger + nut)
                elif self.home_burrow and self.carried_food < 5:
                    # Carry food
                    self.carried_food += 1

                # Seed dropping (20% chance)
                if random.random() < 0.2:
                    world.seeds.append(("bush", self.x, self.y))
                break

        # Deposit food in burrow
        if self.home_burrow and self.carried_food > 0:
            if math.hypot(self.x - self.home_burrow.x, self.y - self.home_burrow.y) < 10:
                self.home_burrow.food_stored += self.carried_food
                self.carried_food = 0

    def reproduce(self, world, animals):
        # Winter reproduction in burrow
        if world.season == "winter" and self.gender == "female" and self.home_burrow and not self.pregnant:
            if len(self.home_burrow.occupants) >= 2: # Has a mate
                self.pregnant = True

        if self.pregnant and world.season == "spring":
            self.pregnant = False
            num_kids = random.randint(2, 5)
            for _ in range(num_kids):
                kid = Rabbit(self.home_burrow.x, self.home_burrow.y)
                kid.mutate()
                kid.home_burrow = self.home_burrow
                animals.append(kid)

class Deer(Animal):
    def __init__(self, x, y):
        super().__init__(x, y, 'deer')
        self.mate = None

    def eat(self, world):
        # Deer eat bushes and trees
        eaten = False
        for tree in world.trees:
            if tree.food_count > 0 and math.hypot(self.x - tree.x, self.y - tree.y) < tree.radius + self.radius:
                nut = tree.eat()
                self.hunger = min(self.max_hunger, self.hunger + nut)
                eaten = True
                break

        if not eaten:
            for bush in world.bushes:
                if bush.food_count > 0 and math.hypot(self.x - bush.x, self.y - bush.y) < bush.radius + self.radius:
                    nut = bush.eat()
                    self.hunger = min(self.max_hunger, self.hunger + nut)
                    if random.random() < 0.2:
                        world.seeds.append(("bush", self.x, self.y))
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
            kid = Deer(self.x, self.y)
            kid.mutate()
            animals.append(kid)

class Wolf(Animal):
    def __init__(self, x, y):
        super().__init__(x, y, 'wolf')
        self.damage = config.ANIMAL_STATS['wolf']['damage']
        self.mate = None
        self.attack_cooldown = 0

    def update(self, world, animals):
        super().update(world, animals)
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

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
            kid = Wolf(self.x, self.y)
            kid.mutate()
            animals.append(kid)

    def hunt(self, animals):
        if self.attack_cooldown <= 0:
            for a in animals:
                if a.species in ['rabbit', 'deer'] and not a.dead:
                    if math.hypot(self.x - a.x, self.y - a.y) < self.radius + a.radius + 5:
                        a.health -= self.damage
                        self.attack_cooldown = 30 # 0.5 sec cooldown

                        if a.health <= 0:
                            a.die()
                            self.hunger = self.max_hunger # Restore hunger upon killing

                            # Negative reinforcement for prey species in this area
                            a.ai.update_memory(a.x, a.y, -5)
                            # Positive reinforcement for wolf
                            self.ai.update_memory(self.x, self.y, +5)
                        break

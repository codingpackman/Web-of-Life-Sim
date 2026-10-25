# Ecosystem Simulator

A visual ecosystem simulator with mammals, birds, fish, predators, and a dynamic four-season environment.

## Features
- **Dynamic Seasons**: Summer, Fall, Winter, Spring. The background color changes, water holes freeze in winter, and plants reproduce/grow based on the season.
- **Plants (Trees & Bushes)**:
  - **Trees**: Consumed leaf-by-leaf by deers. Drops seeds in the Fall based on remaining leaves. Seeds grow in Spring.
  - **Bushes**: Consumed berry-by-berry by rabbits and deers. When eaten, there is a 10% chance an animal drops a seed, which grows into a new bush in the Spring.
- **Terrain**: Includes a bisecting river, scattered water holes (which can freeze), and burrows built dynamically by male rabbits.
- **Animals**:
  - **Rabbit**: Fast sprinting but low stamina. Eats only berries, including stored berries from its own burrow when hungry. Roams for forage close to its burrow, carries berries back (up to 20 stored berries), and hides in its burrow when wolves or snakes are near. Reproduces during winter inside burrows.
  - **Deer**: Large, high health, fast. Eats leaves and berries, roams while full, and increases its urge to explore after staying in an area. Herding is limited to nearby family members; family members can join one another at nearby food and water.
  - **Wolf**: Carnivore. Hunts rabbits and deer; two rabbit meals or one deer meal fill it for the season. It stops hunting while full. Moderately fast with high stamina. Reproduces in the fall.
  - **Fish**: Swim through the river, flee into a one-second underwater dive when threatened, and can only be seen and eaten underwater by snakes. The dive has a four-second cooldown.
  - **Sparrow**: Perches in trees while full, periodically visits trees to seek a nest, flies to water or berry bushes when thirsty or hungry, and returns to its nest tree after drinking or eating.
  - **Hawk**: Patrols while flying, dives at fish and sparrows (not rabbits), lands to drink, and rests in trees between flights. Two fish or sparrows fill it for the season.
  - **Snake**: Hunts fish, rabbits, and sparrows; one successful meal fills it for the season.
- **Starting season**: The first 3,600 ticks are a spring herbivore-only setup period. Wolves, snakes, fish, sparrows, and hawks arrive when summer begins.
- **Evolution & Machine Learning (Lite)**:
  - When animals reproduce, offspring inherit stats from their parents with slight random mutations, enabling "survival of the fittest".
  - Animals possess a spatial memory map. If they experience a negative event (e.g., getting attacked by a wolf), they update that region's value, making them tend to avoid it in the future. Over time, their weights governing attraction/repulsion to stimuli adjust slightly.

## Running the Simulator

Ensure you have `pygame` installed:
```bash
pip install pygame
```

Run the main file:
```bash
python main.py
```

## Tuning Attributes

All constants and tunable parameters are located in `config.py`.
You can adjust:
- Screen dimensions and colors.
- Plant attributes (`TREE_MAX_LEAVES`, `BERRY_NUTRIENT`, etc.).
- Plant reproduction rates: `TREE_SEED_LEAF_INTERVAL` controls how many remaining leaves produce a tree seed, and `BUSH_SEED_DROP_CHANCE` controls the chance that eating a berry drops a bush seed.
- Animal base stats (hunger, speed, stamina, thirst, lifespan, damage) by modifying the `ANIMAL_STATS` dictionary.
- Hawk dive speed, turning limit, duration, hunting cooldown, and sparrow detection range with `HAWK_DIVE_SPEED`, `HAWK_DIVE_TURN_RATE_DEGREES`, `HAWK_DIVE_DURATION`, `HAWK_HUNT_COOLDOWN`, and `HAWK_SPARROW_DETECTION_RANGE`.
- Bird landing cooldown with `BIRD_LANDING_COOLDOWN` (ticks; 120 ticks is 2 seconds at 60 ticks per second).
- Predator full cooldown with `PREDATOR_FULL_COOLDOWN` (ticks; predators stop hunting for this long after becoming full).
- Initial herbivore setup duration and rabbit burrow range with `INITIAL_HERBIVORE_SEASON_TICKS` and `RABBIT_BURROW_RANGE`.
- Fish underwater escape duration, cooldown, and speed with `FISH_DIVE_DURATION`, `FISH_DIVE_COOLDOWN`, and `FISH_UNDERWATER_SPEED`.

`max_hunger` is the animal's full threshold, not a number of ticks. Hunger starts at this value and decreases by `hunger_loss` each simulation tick, so a rabbit with `max_hunger` 100 and `hunger_loss` 0.1 takes about 1,000 ticks to go from full to empty. Eating is available only below the full threshold; the nutrients from a meal can raise hunger above it, after which the animal waits until hunger falls below the threshold before eating again.
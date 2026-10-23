# Ecosystem Simulator

A complete visual simulator of herbivores (Rabbits, Deers) and carnivores (Wolves) interacting within a dynamic, four-season ecosystem.

## Features
- **Dynamic Seasons**: Summer, Fall, Winter, Spring. The background color changes, water holes freeze in winter, and plants reproduce/grow based on the season.
- **Plants (Trees & Bushes)**:
  - **Trees**: Consumed leaf-by-leaf by deers. Drops seeds in the Fall based on remaining leaves. Seeds grow in Spring.
  - **Bushes**: Consumed berry-by-berry by rabbits and deers. When eaten, there is a 20% chance an animal drops a seed, which grows into a new bush in the Spring.
- **Terrain**: Includes a bisecting river, scattered water holes (which can freeze), and burrows built dynamically by male rabbits.
- **Animals**:
  - **Rabbit**: Fast sprinting but low stamina. Eats only berries. Can dig burrows (males) and store food in them. Reproduces during winter inside burrows.
  - **Deer**: Large, high health, fast. Eats leaves and berries. Reproduces in the fall.
  - **Wolf**: Carnivore. Hunts rabbits and deers. Moderately fast with high stamina. Reproduces in the fall.
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
- Animal base stats (hunger, speed, stamina, thirst, lifespan, damage) by modifying the `ANIMAL_STATS` dictionary.
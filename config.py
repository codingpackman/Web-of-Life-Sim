# config.py
# Constants and tunable attributes for the simulator

SCREEN_WIDTH = 1450
SCREEN_HEIGHT = 850
FPS = 60

# Colors
C_BG_SUMMER = (144, 238, 144)    # Light Green
C_BG_FALL = (204, 204, 0)        # Orangy Green / Olive
C_BG_WINTER = (255, 255, 255)    # White
C_BG_SPRING = (34, 139, 34)      # Dark Green

C_TREE = (0, 100, 0)             # Dark Green
C_BUSH = (107, 142, 35)          # Olive Drab
C_BERRY = (128, 0, 128)          # Purple

C_RIVER = (65, 105, 225)         # Royal Blue
C_WATER = (0, 191, 255)          # Deep Sky Blue
C_FROZEN_WATER = (175, 238, 238) # Pale Turquoise
C_BURROW = (139, 69, 19)         # Saddle Brown

C_RABBIT = (200, 200, 200)       # Light Gray
C_DEER = (160, 82, 45)           # Sienna
C_WOLF = (105, 105, 105)         # Dim Gray

# Season lengths in ticks (assuming 60 ticks per second)
SEASON_LENGTH = 60 * 30 # 30 seconds per season

# Plant Attributes
TREE_MAX_LEAVES = 50
TREE_LEAF_NUTRIENT = 20
TREE_SEED_LEAF_INTERVAL = 20
BUSH_MAX_BERRIES = 20
BERRY_NUTRIENT = 50
BUSH_SEED_DROP_CHANCE = 0.1
PLANT_MAX_AGE = 10000

# Animal Base Attributes
ANIMAL_STATS = {
    'rabbit': {
        'max_hunger': 300,
        'hunger_loss': 0.1,
        'health': 20,
        'speed': 1.5,
        'sprint_speed': 4.0,
        'stamina': 50,
        'max_thirst': 300,
        'thirst_loss': 0.1,
        'water_speed': 0.5,
        'lifespan': 10000,
        'radius': 5
    },
    'deer': {
        'max_hunger': 600,
        'hunger_loss': 0.3,
        'health': 100,
        'speed': 2.0,
        'sprint_speed': 3.5,
        'stamina': 100,
        'max_thirst': 300,
        'thirst_loss': 0.2,
        'water_speed': 1.0,
        'lifespan': 15000,
        'radius': 10
    },
    'wolf': {
        'max_hunger': 500,
        'hunger_loss': 0.05,
        'health': 80,
        'speed': 1.6,
        'sprint_speed': 3.25,
        'stamina': 200,
        'max_thirst': 400,
        'thirst_loss': 0.1,
        'water_speed': 0.8,
        'lifespan': 12000,
        'radius': 8,
        'damage': 25
    }
}

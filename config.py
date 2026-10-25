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
SEASON_LENGTH = 3600
DAY_LENGTH = 1800
INITIAL_HERBIVORE_SEASON_TICKS = 3600
RABBIT_BURROW_RANGE = 250
FISH_DIVE_DURATION = 60
FISH_DIVE_COOLDOWN = 240
FISH_UNDERWATER_SPEED = 5.0

# Hawk hunting behavior (dive speed and turn limit apply only while diving).
HAWK_DIVE_SPEED = 5.0
HAWK_DIVE_TURN_RATE_DEGREES = 5
HAWK_DIVE_DURATION = 60
HAWK_HUNT_COOLDOWN = 180
BIRD_LANDING_COOLDOWN = 220
HAWK_SPARROW_DETECTION_RANGE = 120
PREDATOR_FULL_COOLDOWN = SEASON_LENGTH

# Plant Attributes
TREE_MAX_LEAVES = 50
TREE_LEAF_NUTRIENT = 20
TREE_SEED_LEAF_INTERVAL = 20
BUSH_MAX_BERRIES = 10
BERRY_NUTRIENT = 50
BUSH_SEED_DROP_CHANCE = 0.1
BURROW_MAX_FOOD = 20
PLANT_MAX_AGE = 20000

# Animal Base Attributes
ANIMAL_STATS = {
    'rabbit': {
        'max_hunger': 300,
        'hunger_loss': 0.0125,
        'health': 20,
        'speed': 0.75,
        'sprint_speed': 2.5,
        'stamina': 50,
        'max_thirst': 300,
        'thirst_loss': 0.025,
        'water_speed': 0.25,
        'lifespan': 20000,
        'radius': 5
    },
    'deer': {
        'max_hunger': 600,
        'hunger_loss': 0.075,
        'health': 100,
        'speed': 1.0,
        'sprint_speed': 2.00,
        'stamina': 100,
        'max_thirst': 300,
        'thirst_loss': 0.025,
        'water_speed': 1.0,
        'lifespan': 30000,
        'radius': 10
    },
    'wolf': {
        'max_hunger': 500,
        'hunger_loss': 0.0125,
        'health': 80,
        'speed': 0.8,
        'sprint_speed': 1.625,
        'stamina': 200,
        'max_thirst': 400,
        'thirst_loss': 0.025,
        'water_speed': 0.4,
        'lifespan': 30000,
        'radius': 8,
        'damage': 25
        },
    'fish': {
        'max_hunger': 100,
        'hunger_loss': 0,
        'health': 10,
        'speed': 1.5,
        'sprint_speed': 3.0,
        'stamina': 30,
        'max_thirst': 100,
        'thirst_loss': 0,
        'water_speed': 2.0,
        'lifespan': 25000,
        'radius': 4
    },
    'snake': {
        'max_hunger': 200,
        'hunger_loss': 0.005,
        'health': 30,
        'speed': 0.4,
        'sprint_speed': 1.0,
        'stamina': 40,
        'max_thirst': 300,
        'thirst_loss': 0.01,
        'water_speed': 0.4,
        'lifespan': 20000,
        'radius': 4,
        'damage': 15
    },
    'sparrow': {
        'max_hunger': 300,
        'hunger_loss': 0.05,
        'health': 10,
        'speed': 0.5, # slow on ground
        'sprint_speed': 3.0, # fast flying
        'stamina': 500,
        'max_thirst': 300,
        'thirst_loss': 0.02,
        'water_speed': 0,
        'lifespan': 25000,
        'radius': 3
    },
    'hawk': {
        'max_hunger': 500,
        'hunger_loss': 0.05,
        'health': 50,
        'speed': 1.0,
        'sprint_speed': 1.0,
        'stamina': 100,
        'max_thirst': 300,
        'thirst_loss': 0.02,
        'water_speed': 0,
        'lifespan': 30000,
        'radius': 6,
        'damage': 20
    }
}

C_FISH = (255, 165, 0)
C_SNAKE = (128, 0, 128)
C_SPARROW = (139, 69, 19)
C_HAWK = (255, 0, 0)

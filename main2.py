import pygame
import random
import math
import os
from enum import Enum

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
WIDTH = SCREEN_WIDTH
HEIGHT = SCREEN_HEIGHT
BOARD_WIDTH = 800
BOARD_HEIGHT = 800
CARD_WIDTH = 300
CARD_HEIGHT = 400
FPS = 60

# Colors
CANADA_RED = (255, 51, 51)
CANADA_WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
GOLD = (255, 215, 0)
SILVER = (192, 192, 192)
BROWN = (139, 69, 19)
SKY_BLUE = (135, 206, 235)
PINK = (255, 182, 193)
ORANGE = (255, 165, 0)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 128, 0)
BLUE = (0, 0, 255)

# ── Dark-mode palette ─────────────────────────────────────────────────────────
DM_BG         = (18,  18,  28)    # near-black background
DM_SURFACE    = (35,  35,  52)    # card / panel surface
DM_SURFACE2   = (50,  50,  70)    # lighter panel
DM_TEXT       = (220, 220, 235)   # primary text
DM_BORDER     = (90,  90, 120)    # border / outline
DM_HIGHLIGHT  = (80, 120, 200)    # accent / highlight

def theme(color, dark_mode):
    """Swap common colors to their dark-mode equivalents."""
    if not dark_mode:
        return color
    mapping = {
        CANADA_WHITE: DM_SURFACE,
        (255,255,255): DM_SURFACE,
        LIGHT_GRAY:   DM_SURFACE2,
        (200,200,200):DM_SURFACE2,
        BLACK:        DM_TEXT,
        (0,0,0):      DM_TEXT,
        GRAY:         DM_BORDER,
        (128,128,128):DM_BORDER,
    }
    return mapping.get(color, color)

# Dice Types
class DiceType(Enum):
    REGULAR = "Regular Dice"
    STABLE = "Stable Dice (3s & 4s)"
    HIGH_EXPLOSIVE = "High Explosives!!"
    pass

# Typical rent/prices matrix (user-provided) used as baseline rent tiers per board position
TYPICAL_RENTS = [["no"], [2, 10, 30, 90, 160, 250], ["no"],
        [4, 20, 60, 180, 320, 450], ["no"], [25, 50, 100, 200],
        [6, 30, 90, 270, 400, 550], ["no"], [6, 30, 90, 270, 400, 550],
        [8, 40, 100, 300, 450, 600], ["no"], [10, 50, 150, 450, 625, 750],
        [4, 10], [10, 50, 150, 450, 625, 750], [12, 60, 180, 500, 700, 900],
        [25, 50, 100, 200], [14, 70, 200, 550, 750, 950], ["no"],
        [14, 70, 200, 550, 750, 950], [16, 80, 220, 600, 800, 1000], ["no"],
        [18, 90, 250, 700, 875, 1050], ["no"], [18, 90, 250, 700, 875, 1050],
        [20, 100, 300, 750, 925, 1100], [25, 50, 100, 200],
        [22, 110, 330, 800, 975, 1150], [22, 110, 330, 800, 975, 1150],
        [4, 10], [24, 120, 360, 850, 1025], ["no"],
        [26, 130, 390, 900, 1100, 1275], [26, 130, 390, 900, 1100, 1275],
        ["no"], [28, 150, 450, 1000, 1200, 1400], [25, 50, 100, 200], ["no"],
        [35, 175, 500, 1100, 1300, 1500], ["no"],
        [50, 200, 600, 1400, 1700, 2000]]

# House/Hotel pool (bank supply)
HOUSE_POOL = 32
HOTEL_POOL = 12

# Property Types
class PropertyType(Enum):
    PROPERTY = "property"
    TRAIN_STATION = "train_station"
    UTILITY = "utility"
    CHEST = "chest"
    CHANCE = "chance"
    JAIL = "jail"
    GO = "go"
    GO_TO_US = "go_to_us"
    FREE_PARKING = "free_parking"

# Property Class
class Property:
    def __init__(self, name, price, color, property_type=PropertyType.PROPERTY, base_rent=0, position=None):
        self.name = name
        self.price = price
        self.color = color
        self.property_type = property_type
        self.owner = None
        self.houses = 0
        self.hotel = False
        self.mortgaged = False
        self.base_rent = base_rent
        self.stock_value = price
        self.position = position

    def get_base_build_cost(self):
        return max(50, self.price // 4)

    def get_house_cost(self):
        if self.property_type != PropertyType.PROPERTY or self.hotel or self.houses >= 4:
            return None
        base_cost = self.get_base_build_cost()
        return int(round(base_cost * (1.3 ** self.houses)))

    def get_hotel_cost(self):
        if self.property_type != PropertyType.PROPERTY or self.hotel or self.houses != 4:
            return None
        base_cost = self.get_base_build_cost()
        return int(round(base_cost * (1.3 ** 4) * 2))

    def get_income_multiplier(self):
        multiplier = 1.3 ** self.houses
        if self.hotel:
            multiplier *= 2
        return multiplier

    def get_rent(self, dice_total=0):
        if self.mortgaged:
            return 0
            
        if self.property_type == PropertyType.TRAIN_STATION:
            stations = [p for p in properties if p.property_type == PropertyType.TRAIN_STATION and p.owner == self.owner]
            return 25 * (2 ** (len(stations) - 1))
            
        elif self.property_type == PropertyType.UTILITY:
            utilities = [p for p in properties if p.property_type == PropertyType.UTILITY and p.owner == self.owner]
            multiplier = 10 if len(utilities) == 2 else 4
            return multiplier * max(1, dice_total)
            
        else:
            try:
                matrix = TYPICAL_RENTS[self.position]
            except Exception:
                matrix = [self.base_rent]

            if isinstance(matrix, list) and len(matrix) > 0 and matrix[0] == "no":
                stock_adjusted_base = max(1, int(round(self.base_rent * (self.stock_value / max(1, self.price)))))
                return int(round(stock_adjusted_base * self.get_income_multiplier()))

            if self.hotel:
                tier_value = matrix[-1]
            elif self.houses > 0:
                idx = min(self.houses, len(matrix) - 1)
                tier_value = matrix[idx]
            else:
                tier_value = matrix[0]

            stock_adjusted = max(0, int(round(tier_value * (self.stock_value / max(1, self.price)))))
            return stock_adjusted

    def build_house(self):
        global HOUSE_POOL
        if self.property_type == PropertyType.PROPERTY and self.houses < 4 and not self.hotel and HOUSE_POOL > 0:
            self.houses += 1
            HOUSE_POOL -= 1
            return True
        return False

    def build_hotel(self):
        global HOTEL_POOL, HOUSE_POOL
        if self.property_type == PropertyType.PROPERTY and self.houses == 4 and not self.hotel and HOTEL_POOL > 0:
            self.hotel = True
            self.houses = 0
            HOTEL_POOL -= 1
            HOUSE_POOL += 4
            return True
        return False
    
    def update_stock_value(self, percent_change):
        self.stock_value = int(self.stock_value * (1 + percent_change / 100))
        self.stock_value = max(10, self.stock_value)

    def get_mortgage_value(self):
        return self.price // 2

    def get_unmortgage_cost(self):
        return int(round(self.get_mortgage_value() * 1.1))

    def mortgage(self):
        if self.mortgaged:
            return None
        if self.houses > 0 or self.hotel:
            return None
        self.mortgaged = True
        return self.get_mortgage_value()

    def unmortgage(self):
        if not self.mortgaged:
            return None
        cost = self.get_unmortgage_cost()
        self.mortgaged = False
        return cost

    def sell_house(self):
        global HOUSE_POOL, HOTEL_POOL
        if self.houses > 0:
            last_cost = int(round(self.get_base_build_cost() * (1.3 ** (self.houses - 1))))
            gain = last_cost // 2
            self.houses -= 1
            HOUSE_POOL += 1
            return gain
        if self.hotel:
            if HOUSE_POOL < 4:
                return 0
            base_cost = self.get_base_build_cost()
            hotel_cost = int(round(base_cost * (1.3 ** 4) * 2))
            gain = hotel_cost // 2
            self.hotel = False
            self.houses = 4
            HOTEL_POOL += 1
            HOUSE_POOL -= 4
            return gain
        return 0

    def sell_property_to_bank(self):
        if self.houses > 0 or self.hotel:
            return None
        sell_amount = self.price // 2
        if self.mortgaged:
            return None
        return sell_amount


# Player Class
class Player:
    def __init__(self, name, color, token):
        self.name = name
        self.color = color
        self.token = token
        self.position = 0
        self.money = 500
        self.properties = []
        self.in_jail = False
        self.jail_turns = 0
        self.consecutive_doubles = 0
        self.get_out_of_jail_free = 0
        self.next_roll_max_one = False
        # Animation state for smooth/hopping movement
        self.animating = False
        self.anim_path = []        # list of position indices to traverse (in order)
        self.anim_step = 0         # current step index in anim_path
        self.anim_frame = 0        # current frame within the step
        self.anim_frames_per_step = 8
        self.anim_hop_height = 18  # pixels of hop peak
        self.anim_pending_landing = None  # final landing position to handle after animation
        
    def move(self, spaces):
        self.position = (self.position + spaces) % len(board_spaces)
        return self.position
    
    def pay(self, amount, recipient=None):
        if self.money >= amount:
            self.money -= amount
            if recipient:
                recipient.money += amount
            return True
        return False
    
    def receive(self, amount):
        self.money += amount


# Dice Class
class Dice:
    def __init__(self):
        self.dice_type = DiceType.REGULAR
        self.roll_result = (0, 0)
        self.double_count = 0
        
    def roll(self):
        if self.dice_type == DiceType.REGULAR:
            die1 = random.randint(1, 6)
            die2 = random.randint(1, 6)
            
        elif self.dice_type == DiceType.STABLE:
            # Physical die: three 3-faces and three 4-faces
            die1 = random.choice([3, 3, 3, 4, 4, 4])
            die2 = random.choice([3, 3, 3, 4, 4, 4])

        elif self.dice_type == DiceType.HIGH_EXPLOSIVE:
            # Physical die: three 1-faces and three 6-faces
            die1 = random.choice([1, 1, 1, 6, 6, 6])
            die2 = random.choice([1, 1, 1, 6, 6, 6])
        
        self.roll_result = (die1, die2)
        return die1 + die2, die1 == die2
    
    def change_dice_type(self):
        types = list(DiceType)
        current_index = types.index(self.dice_type)
        self.dice_type = types[(current_index + 1) % len(types)]
        return self.dice_type


# Game Board Spaces
def create_board():
    spaces = [
        {"name": "GO (MathHacks)", "type": PropertyType.GO, "color": GOLD},
        {"name": "STC", "type": PropertyType.PROPERTY, "price": 60, "color": BROWN, "base_rent": 4},
        {"name": "Item Chest", "type": PropertyType.CHEST, "color": LIGHT_GRAY},
        {"name": "Fairview Mall", "type": PropertyType.PROPERTY, "price": 60, "color": BROWN, "base_rent": 2},
        {"name": "Income Tax", "type": "tax", "color": GRAY},
        {"name": "York University", "type": PropertyType.TRAIN_STATION, "price": 200, "color": BLACK},
        {"name": "Little Italy", "type": PropertyType.PROPERTY, "price": 100, "color": SKY_BLUE, "base_rent": 6},
        {"name": "Chance", "type": PropertyType.CHANCE, "color": LIGHT_GRAY},
        {"name": "Chinatown", "type": PropertyType.PROPERTY, "price": 100, "color": SKY_BLUE, "base_rent": 6},
        {"name": "Greektown", "type": PropertyType.PROPERTY, "price": 120, "color": SKY_BLUE, "base_rent": 8},
        {"name": "Jail (Arctic)", "type": PropertyType.JAIL, "color": GRAY},
        {"name": "Harvey's", "type": PropertyType.PROPERTY, "price": 140, "color": PINK, "base_rent": 10},
        {"name": "407 ETR", "type": PropertyType.UTILITY, "price": 150, "color": GRAY},
        {"name": "Frankie Tomatto's", "type": PropertyType.PROPERTY, "price": 140, "color": PINK, "base_rent": 10},
        {"name": "Distillery District", "type": PropertyType.PROPERTY, "price": 160, "color": PINK, "base_rent": 12},
        {"name": "University of Toronto", "type": PropertyType.TRAIN_STATION, "price": 200, "color": BLACK},
        {"name": "Marineland", "type": PropertyType.PROPERTY, "price": 220, "color": RED, "base_rent": 18},
        {"name": "Item Chest", "type": PropertyType.CHEST, "color": LIGHT_GRAY},
        {"name": "Scarborough", "type": PropertyType.PROPERTY, "price": 180, "color": ORANGE, "base_rent": 14},
        {"name": "Markham", "type": PropertyType.PROPERTY, "price": 200, "color": ORANGE, "base_rent": 16},
        {"name": "Free Parking", "type": PropertyType.FREE_PARKING, "color": GRAY},
        {"name": "Canada's Wonderland", "type": PropertyType.PROPERTY, "price": 220, "color": RED, "base_rent": 18},
        {"name": "Chance", "type": PropertyType.CHANCE, "color": LIGHT_GRAY},
        {"name": "Vaughan", "type": PropertyType.PROPERTY, "price": 180, "color": ORANGE, "base_rent": 14},
        {"name": "Calgary Stampede", "type": PropertyType.PROPERTY, "price": 240, "color": RED, "base_rent": 20},
        {"name": "TMU", "type": PropertyType.TRAIN_STATION, "price": 200, "color": BLACK},
        {"name": "Toronto Raptors", "type": PropertyType.PROPERTY, "price": 260, "color": YELLOW, "base_rent": 22},
        {"name": "Maple Leafs", "type": PropertyType.PROPERTY, "price": 260, "color": YELLOW, "base_rent": 22},
        {"name": "401", "type": PropertyType.UTILITY, "price": 150, "color": GRAY},
        {"name": "Blue Jays", "type": PropertyType.PROPERTY, "price": 280, "color": YELLOW, "base_rent": 24},
        {"name": "Go to US", "type": PropertyType.GO_TO_US, "color": GRAY},
        {"name": "Ripley's Aquarium", "type": PropertyType.PROPERTY, "price": 300, "color": GREEN, "base_rent": 26},
        {"name": "Centre Island", "type": PropertyType.PROPERTY, "price": 300, "color": GREEN, "base_rent": 26},
        {"name": "Item Chest", "type": PropertyType.CHEST, "color": LIGHT_GRAY},
        {"name": "Ontario Science Centre", "type": PropertyType.PROPERTY, "price": 320, "color": GREEN, "base_rent": 28},
        {"name": "University of Waterloo", "type": PropertyType.TRAIN_STATION, "price": 200, "color": BLACK},
        {"name": "Chance", "type": PropertyType.CHANCE, "color": LIGHT_GRAY},
        {"name": "CN Tower", "type": PropertyType.PROPERTY, "price": 350, "color": BLUE, "base_rent": 35},
        {"name": "Luxury Tax", "type": "tax", "color": GRAY},
        {"name": "Rogers Centre", "type": PropertyType.PROPERTY, "price": 400, "color": BLUE, "base_rent": 50}
    ]
    return spaces


# Create properties list
board_spaces = create_board()
properties = []
for i, space in enumerate(board_spaces):
    if space["type"] == PropertyType.PROPERTY:
        prop = Property(space["name"], space["price"], space["color"], 
                       PropertyType.PROPERTY, space["base_rent"], position=i)
        properties.append(prop)
        board_spaces[i]["property"] = prop
    elif space["type"] in [PropertyType.TRAIN_STATION, PropertyType.UTILITY]:
        prop = Property(space["name"], space["price"], space["color"], space["type"], position=i)
        properties.append(prop)
        board_spaces[i]["property"] = prop


# Item Chest Cards
item_chest_cards = [
    {"name": "Outlier Clamp", "description": "Force your next outcome to be at most 1", 
     "action": "rigged_dice"},
    {"name": "Variance Eraser", "description": "Delete one house placed on someone's property",
     "action": "evaporator"},
    {"name": "Bernoulli Trial", "description": "Flip a fair coin: Heads = extra turn, Tails = lose turn",
     "action": "coin_flip"},
    {"name": "Compound Growth", "description": "Gain a 10% wealth boost",
     "action": "coin_bag"}
]

# ─────────────────────────────────────────────────────────────────────────────
# CHANCE / FATE CARDS  (weighted draw system)
# 35%  →  Market-effect cards  (inflation / market_drop)
# 35%  →  Money-transfer cards  (canada_gold, friend_money, bake_sale, jackpot,
#                                 mr_monopoly_tax, wheel_fortune, concert_tickets,
#                                 spare_money, party_money, huge_apology)
# 30%  →  Special-action cards  (hackathon_laptop, evaporator_chance,
#                                 coin_flip_chance, coin_bag_chance)
# ─────────────────────────────────────────────────────────────────────────────

CHANCE_CATEGORIES = {
    "market": {
        "weight": 35,
        "cards": [
            {
                "name": "Inflation",
                "description": "Housing prices increase +50% to +100% for 2–4 turns!",
                "action": "inflation"
            },
            {
                "name": "Market Drop",
                "description": "Housing prices decrease -25% to -50% for 2–4 turns!",
                "action": "market_drop"
            },
        ]
    },
    "money": {
        "weight": 35,
        "cards": [
            {
                "name": "Canada Wins Gold!",
                "description": "Gain $100.",
                "action": "canada_gold"
            },
            {
                "name": "Your Friend Needs Money",
                "description": "Lose $25.",
                "action": "friend_money"
            },
            {
                "name": "School Bake Sale",
                "description": "Your school hosted a bake sale. Gain $10.",
                "action": "bake_sale"
            },
            {
                "name": "Jackpot!",
                "description": "You hit the jackpot! Gain $200.",
                "action": "jackpot"
            },
            {
                "name": "Mr. Monopoly's Tax",
                "description": "Mr. Monopoly is taxing you. Lose $100.",
                "action": "mr_monopoly_tax"
            },
            {
                "name": "Wheel of Fortune",
                "description": "You spun the wheel of fortune! Gain $50.",
                "action": "wheel_fortune"
            },
            {
                "name": "Concert Tickets",
                "description": "You bought concert tickets. Lose $50.",
                "action": "concert_tickets"
            },
            {
                "name": "Spare Change",
                "description": "You collected some spare money. Collect $10 from each player.",
                "action": "spare_money"
            },
            {
                "name": "Party Host",
                "description": "You need money to host a party. Collect $25 from each player.",
                "action": "party_money"
            },
            {
                "name": "Huge Apology",
                "description": "You owe a huge apology to the world. Pay $50 to each player.",
                "action": "huge_apology"
            },
        ]
    },
    "special": {
        "weight": 30,
        "cards": [
            {
                "name": "Hackathon Laptop",
                "description": "Pick a roll number between 1 and 12. Move to that space!",
                "action": "hackathon_laptop"
            },
            {
                "name": "Evaporator",
                "description": "Delete one house from any property on the board!",
                "action": "evaporator_chance"
            },
            {
                "name": "Coin Flip",
                "description": "Flip a coin: Heads = extra turn, Tails = lose a turn.",
                "action": "coin_flip_chance"
            },
            {
                "name": "Coin Bag",
                "description": "Gives you 10% more money!",
                "action": "coin_bag_chance"
            },
        ]
    },
}


def draw_chance_card():
    """Pick a weighted category, then a random card from that category."""
    categories = list(CHANCE_CATEGORIES.keys())
    weights = [CHANCE_CATEGORIES[c]["weight"] for c in categories]
    chosen_category = random.choices(categories, weights=weights, k=1)[0]
    card = random.choice(CHANCE_CATEGORIES[chosen_category]["cards"])
    return card


# Active market effects: list of dicts {"action": ..., "turns_left": N, "amount": X}
active_market_effects = []


def apply_market_effects():
    """Apply ongoing market effects and decrement their timers. Call once per turn."""
    global active_market_effects
    expired = []
    for effect in active_market_effects:
        for prop in properties:
            if effect["action"] == "inflation":
                prop.update_stock_value(effect["amount"])
            elif effect["action"] == "market_drop":
                prop.update_stock_value(-effect["amount"])
        effect["turns_left"] -= 1
        if effect["turns_left"] <= 0:
            expired.append(effect)
    for e in expired:
        active_market_effects.remove(e)


# Main Game Class
class CanadaMonopoly:
    def __init__(self, num_players=2):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Canada Monopoly - Probability & Statistics Lab")
        self.clock = pygame.time.Clock()
        
        # Load Futura font from assets
        futura_path = os.path.join("assets", "Futura.ttf")
        try:
            self.font = pygame.font.Font(futura_path, 20)
            self.big_font = pygame.font.Font(futura_path, 32)
            self.title_font = pygame.font.Font(futura_path, 44)
        except Exception:
            self.font = pygame.font.Font(None, 20)
            self.big_font = pygame.font.Font(None, 32)
            self.title_font = pygame.font.Font(None, 44)
        board_size = min(SCREEN_HEIGHT - 80, SCREEN_WIDTH - 380)
        self.board_rect = pygame.Rect(30, 40, board_size, board_size)
        self.info_x = self.board_rect.right + 25
        self.info_y = 50
        self.roll_button = pygame.Rect(self.info_x, self.info_y + 120, 150, 40)
        self.dice_button = pygame.Rect(self.info_x, self.info_y + 170, 150, 40)
        self.trade_button = pygame.Rect(self.info_x, self.info_y + 640, 150, 40)
        self.bankrupt_button = pygame.Rect(self.info_x, self.info_y + 690, 150, 40)
        self.buy_button = pygame.Rect(self.info_x, self.info_y + 340, 150, 40)
        self.skip_button = pygame.Rect(self.info_x, self.info_y + 390, 150, 40)
        self.auction_button = pygame.Rect(self.info_x, self.info_y + 440, 150, 40)
        self.house_button = pygame.Rect(self.info_x, self.info_y + 520, 150, 40)
        self.hotel_button = pygame.Rect(self.info_x, self.info_y + 570, 150, 40)
        self.raise_5_button = pygame.Rect(0, 0, 100, 36)
        self.raise_20_button = pygame.Rect(0, 0, 100, 36)
        self.raise_100_button = pygame.Rect(0, 0, 110, 36)
        self.leave_auction_button = pygame.Rect(0, 0, 110, 36)
        self.sell_house_button = pygame.Rect(self.info_x, self.info_y + 430, 150, 36)
        self.sell_property_button = pygame.Rect(self.info_x, self.info_y + 470, 150, 36)
        self.mortgage_button = pygame.Rect(self.info_x, self.info_y + 510, 150, 36)

        # Dark mode & settings
        self.dark_mode = False
        self.settings_open = False
        self.stats_button = pygame.Rect(SCREEN_WIDTH - 220, 10, 100, 32)
        self.settings_button = pygame.Rect(SCREEN_WIDTH - 110, 10, 100, 32)
        self.settings_darkmode_btn = pygame.Rect(0, 0, 200, 36)

        # Hackathon laptop: pending position pick (1-12)
        self.hackathon_pending = False
        self.hackathon_player = None
        self.hackathon_buttons = []

        # Evaporator (chance version): pending house removal
        self.evaporator_pending = False
        self.evaporator_player = None
        self.evaporator_prop_rects = []
        
        self.players = []
        self.current_player_index = 0
        self.dice = Dice()
        self.game_over = False
        self.winner = None
        self.message = ""
        self.message_timer = 0
        self.waiting_for_action = True
        self.dice_rolled = False
        self.roll_value = 0
        self.is_double = False
        self.pending_property = None
        self.hovered_position = None
        self.auction_active = False
        self.auction_property = None
        self.auction_current_bid = 0
        self.auction_highest_bidder = None
        self.auction_turn_index = 0
        self.auction_active_players = []
        self.trade_active = False
        self.auction_timer = 0          # countdown frames; reset each bidder turn
        self.auction_turn_seconds = 5   # seconds per bidder
        self.trade_stage = "select"
        self.trade_partner_index = None
        self.trade_offer_props = set()
        self.trade_request_props = set()
        self.trade_offer_cash = 0
        self.trade_request_cash = 0
        self.trade_dragging = None
        self.trade_offer_prop_rects = []
        self.trade_request_prop_rects = []
        self.trade_partner_rects = []
        self.trade_accept_button = pygame.Rect(0, 0, 120, 36)
        self.trade_decline_button = pygame.Rect(0, 0, 120, 36)
        self.trade_propose_button = pygame.Rect(0, 0, 140, 36)
        self.num_players = num_players
        self.probability_panel_open = False
        self.roll_count = 0
        self.roll_sum_total = 0
        self.doubles_count = 0
        self.roll_total_counts = {n: 0 for n in range(2, 13)}
        self.last_rolls = []
        self.position_visit_counts = {i: 0 for i in range(len(board_spaces))}
        
        # Animation state for player movement
        self.player_animations = {}  # {player_id: {start_pos, end_pos, progress}}
        self.animation_duration = 20  # frames for jump animation

        self.dice_face_size = 42
        self.dice_face_images = {}
        dice_face_files = {
            1: "dice-six-faces-one.png",
            2: "dice-six-faces-two.png",
            3: "dice-six-faces-three.png",
            4: "dice-six-faces-four.png",
            5: "dice-six-faces-five.png",
            6: "dice-six-faces-six.png",
        }
        for value, file_name in dice_face_files.items():
            die_path = os.path.join("assets", file_name)
            try:
                loaded_die = pygame.image.load(die_path).convert_alpha()
                self.dice_face_images[value] = pygame.transform.smoothscale(
                    loaded_die,
                    (self.dice_face_size, self.dice_face_size)
                )
            except Exception:
                self.dice_face_images[value] = None

        self.board_overlay_image = None
        overlay_path = os.path.join("assets", "board.png")
        try:
            loaded_overlay = pygame.image.load(overlay_path).convert()
            self.board_overlay_image = pygame.transform.smoothscale(
                loaded_overlay,
                (self.board_rect.width, self.board_rect.height)
            )
        except Exception:
            self.board_overlay_image = None
        
        self.setup_game()

    def set_message(self, text, duration=180):
        self.message = text
        self.message_timer = duration

    def get_dice_total_distribution(self, dice_type):
        if dice_type == DiceType.REGULAR:
            weights = {1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1}
        elif dice_type == DiceType.STABLE:
            weights = {3: 3, 4: 3}
        else:
            weights = {1: 3, 6: 3}

        distribution = {}
        total_outcomes = sum(weights.values()) ** 2
        for a, wa in weights.items():
            for b, wb in weights.items():
                total = a + b
                distribution[total] = distribution.get(total, 0.0) + (wa * wb) / total_outcomes
        return distribution

    def get_expected_roll(self, dice_type):
        distribution = self.get_dice_total_distribution(dice_type)
        return sum(total * prob for total, prob in distribution.items())

    def get_roll_variance(self, dice_type):
        distribution = self.get_dice_total_distribution(dice_type)
        mean = self.get_expected_roll(dice_type)
        return sum(((total - mean) ** 2) * prob for total, prob in distribution.items())

    def get_doubles_probability(self, dice_type):
        if dice_type == DiceType.REGULAR:
            return 1 / 6
        return 1 / 2

    def record_roll_stats(self, roll_value, is_double, landing_pos):
        self.roll_count += 1
        self.roll_sum_total += roll_value
        if roll_value in self.roll_total_counts:
            self.roll_total_counts[roll_value] += 1
        if is_double:
            self.doubles_count += 1
        self.last_rolls.append(roll_value)
        if len(self.last_rolls) > 12:
            self.last_rolls.pop(0)
        if landing_pos is not None and landing_pos in self.position_visit_counts:
            self.position_visit_counts[landing_pos] += 1
        
    def setup_game(self):
        player_colors = [CANADA_RED, BLUE, GREEN, GOLD]
        player_tokens = ["▲", "●", "■", "♦"]
        for i in range(self.num_players):
            player = Player(f"Player {i+1}", player_colors[i], player_tokens[i])
            self.players.append(player)
        
    def handle_item_chest(self, player):
        card = item_chest_cards.pop(0)
        item_chest_cards.append(card)
        
        self.set_message(f"Item Chest Experiment: {card['name']}")
        
        if card['action'] == "rigged_dice":
            player.next_roll_max_one = True
            self.set_message("Outlier Clamp! Your next roll is capped at 1.")
            
        elif card['action'] == "evaporator":
            self.set_message("Item Chest: Evaporator (not implemented) - no effect this turn")
            
        elif card['action'] == "coin_flip":
            result = random.choice(["Heads", "Tails"])
            if result == "Heads":
                self.set_message("Heads! You get an extra turn!")
                self.extra_turn = True
            else:
                self.set_message("Tails! You lose a turn!")
                self.lose_turn = True
                
        elif card['action'] == "coin_bag":
            bonus = int(player.money * 0.1)
            player.receive(bonus)
            self.set_message(f"Coin Bag: You got ${bonus} (10% bonus)!")

    # ─────────────────────────────────────────────────────────────────────────
    # CHANCE / FATE CARD HANDLER
    # ─────────────────────────────────────────────────────────────────────────
    def handle_chance(self, player):
        card = draw_chance_card()
        action = card["action"]

        # Show card name + description at the top
        self.set_message(f"Stat Event – {card['name']}: {card['description']}", 240)

        # ── Market effects (35%) ──────────────────────────────────────────────
        if action == "inflation":
            pct = random.randint(50, 100)
            turns = random.randint(2, 4)
            active_market_effects.append({"action": "inflation", "amount": pct, "turns_left": turns})
            # Apply immediately this turn too
            for prop in properties:
                prop.update_stock_value(pct)
            self.set_message(f"Inflation! Property values +{pct}% for {turns} turns!", 240)

        elif action == "market_drop":
            pct = random.randint(25, 50)
            turns = random.randint(2, 4)
            active_market_effects.append({"action": "market_drop", "amount": pct, "turns_left": turns})
            for prop in properties:
                prop.update_stock_value(-pct)
            self.set_message(f"Market Drop! Property values -{pct}% for {turns} turns!", 240)

        # ── Money-transfer cards (35%) ────────────────────────────────────────
        elif action == "canada_gold":
            player.receive(100)
            self.set_message("Canada Wins Gold! You gained $100!")

        elif action == "friend_money":
            amt = min(25, player.money)
            player.pay(amt)
            self.set_message("Your friend needs $25. You lost $25.")

        elif action == "bake_sale":
            player.receive(10)
            self.set_message("School bake sale raised money! You gained $10.")

        elif action == "jackpot":
            player.receive(200)
            self.set_message("JACKPOT! You gained $200!")

        elif action == "mr_monopoly_tax":
            amt = min(100, player.money)
            player.pay(amt)
            self.set_message("Mr. Monopoly is taxing you $100!")

        elif action == "wheel_fortune":
            player.receive(50)
            self.set_message("Wheel of Fortune! You gained $50!")

        elif action == "concert_tickets":
            amt = min(50, player.money)
            player.pay(amt)
            self.set_message("You bought concert tickets. Lost $50.")

        elif action == "spare_money":
            collected = 0
            for other in self.players:
                if other != player:
                    paid = min(10, other.money)
                    other.pay(paid)
                    player.receive(paid)
                    collected += paid
            self.set_message(f"Collected spare change! Got ${collected} total (${10} per player).")

        elif action == "party_money":
            collected = 0
            for other in self.players:
                if other != player:
                    paid = min(25, other.money)
                    other.pay(paid)
                    player.receive(paid)
                    collected += paid
            self.set_message(f"Party time! Collected ${collected} total (${25} per player).")

        elif action == "huge_apology":
            total_paid = 0
            for other in self.players:
                if other != player:
                    amt = min(50, player.money)
                    if player.money >= 50:
                        player.pay(50, other)
                        total_paid += 50
                    else:
                        player.pay(player.money, other)
                        total_paid += amt
            self.set_message(f"Huge Apology! You paid $50 to each other player (${total_paid} total).")

        # ── Special-action cards (30%) ────────────────────────────────────────
        elif action == "hackathon_laptop":
            self.set_message("Hackathon Laptop! Choose a number 1–12 to move to that space!", 999999)
            self.hackathon_pending = True
            self.hackathon_player = player
            self.waiting_for_action = False

        elif action == "evaporator_chance":
            # Find all properties with houses/hotels
            buildable = [p for p in properties if (p.houses > 0 or p.hotel) and p.owner is not None]
            if not buildable:
                self.set_message("Evaporator: No houses on the board to remove!")
            else:
                self.set_message("Evaporator! Click a property to remove one house/hotel.", 999999)
                self.evaporator_pending = True
                self.evaporator_player = player
                self.waiting_for_action = False

        elif action == "coin_flip_chance":
            result = random.choice(["Heads", "Tails"])
            if result == "Heads":
                self.set_message(f"Coin Flip – Heads! {player.name} gets an extra turn!")
                self.extra_turn = True
            else:
                self.set_message(f"Coin Flip – Tails! {player.name} loses a turn!")
                self.lose_turn = True

        elif action == "coin_bag_chance":
            bonus = int(player.money * 0.1)
            player.receive(bonus)
            self.set_message(f"Coin Bag! You got +10% money (${bonus})!")

    def handle_landing(self, player, position):
        space = board_spaces[position]
        
        if position == 0 and not self.just_passed_go:
            player.receive(300)
            self.set_message("Landed on GO! Received $300!")
        
        if "property" in space:
            prop = space["property"]
            
            if prop.owner is None:
                if player.money < prop.price:
                    self.set_message(f"{prop.name} costs ${prop.price}. Starting auction.")
                    self.start_auction(prop)
                else:
                    self.waiting_for_action = False
                    self.pending_property = prop
                    self.set_message(f"{prop.name} is unowned. Buy for ${prop.price}, auction, or skip.", 100000)
                
            elif prop.owner != player:
                rent = prop.get_rent()
                if player.pay(rent, prop.owner):
                    self.set_message(f"Paid ${rent} rent to {prop.owner.name}")
                else:
                    self.set_message(f"{player.name} can't pay rent! Bankruptcy!")
                    self.handle_bankruptcy(player)
        
        elif space["type"] == PropertyType.CHEST:
            self.handle_item_chest(player)
            
        elif space["type"] == PropertyType.CHANCE:
            self.handle_chance(player)
            
        elif space["type"] == PropertyType.GO_TO_US:
            player.position = 10
            player.in_jail = True
            self.set_message("Go to US! Sent to the Arctic! Pay $50 to fly back")
            
        elif space["type"] == PropertyType.JAIL:
            if player.in_jail:
                player.jail_turns += 1
                self.set_message(f"{player.name} is in jail. Turn {player.jail_turns}/3")
        
        elif space["type"] == "tax":
            if space["name"] == "Income Tax":
                player.pay(200, None)
                self.set_message("Paid $200 Income Tax")
            else:
                player.pay(100, None)
                self.set_message("Paid $100 Luxury Tax")
    
    def handle_bankruptcy(self, player):
        self.players.remove(player)
        if len(self.players) == 1:
            self.game_over = True
            self.winner = self.players[0]
            self.set_message(f"{self.players[0].name} wins!", 100000)

    def force_bankruptcy_if_needed(self):
        if self.game_over or not self.players:
            return
        current_player = self.players[self.current_player_index]
        if current_player.money < 0:
            current_player.money = 0
            self.set_message(f"{current_player.name} went bankrupt!")
            self.handle_bankruptcy(current_player)

    def start_auction(self, prop):
        self.auction_active = True
        self.auction_property = prop
        self.auction_current_bid = max(1, prop.price // 2)
        self.auction_highest_bidder = None
        self.auction_active_players = [p for p in self.players if p.money > 0]
        self.auction_turn_index = 0
        self.auction_timer = self.auction_turn_seconds * FPS
        self.pending_property = None
        self.waiting_for_action = False

    def finish_auction(self):
        if self.auction_highest_bidder:
            self.auction_highest_bidder.pay(self.auction_current_bid)
            self.auction_property.owner = self.auction_highest_bidder
            self.auction_highest_bidder.properties.append(self.auction_property)
            self.set_message(
                f"{self.auction_highest_bidder.name} won {self.auction_property.name} for ${self.auction_current_bid}.")
        else:
            self.set_message(f"No bids for {self.auction_property.name}.")
        self.auction_active = False
        self.auction_property = None
        self.auction_current_bid = 0
        self.auction_highest_bidder = None
        self.auction_active_players = []
        self.auction_turn_index = 0
        self.waiting_for_action = True

    def get_current_auction_player(self):
        if not self.auction_active_players:
            return None
        self.auction_turn_index %= len(self.auction_active_players)
        return self.auction_active_players[self.auction_turn_index]

    def advance_auction_turn(self):
        if not self.auction_active_players:
            self.finish_auction()
            return
        if len(self.auction_active_players) == 1:
            self.finish_auction()
            return
        self.auction_turn_index = (self.auction_turn_index + 1) % len(self.auction_active_players)
        self.auction_timer = self.auction_turn_seconds * FPS

    def get_hovered_position(self, mouse_pos):
        for position in range(len(board_spaces)):
            if self.get_space_rect(position).collidepoint(mouse_pos):
                return position
        return None

    def get_hovered_property(self):
        if self.hovered_position is None:
            return None
        space = board_spaces[self.hovered_position]
        return space.get("property")

    def get_property_tooltip_lines(self, prop):
        owner_name = prop.owner.name if prop.owner else "None"
        lines = [prop.name]
        lines.append(f"Owner: {owner_name}")
        lines.append(f"Price: ${prop.price}")
        lines.append(f"Stock Value: ${prop.stock_value}")
        lines.append(f"Rent: ${prop.get_rent(self.roll_value)}")
        lines.append(f"Full set: {'Yes' if prop.owner and self.owns_color_set(prop.owner, prop) else 'No'}")
        lines.append(f"Houses: {prop.houses}/4  Hotel: {'Yes' if prop.hotel else 'No'}")
        lines.append(f"Mortgaged: {'Yes' if prop.mortgaged else 'No'}")
        house_cost = prop.get_house_cost()
        hotel_cost = prop.get_hotel_cost()
        lines.append(f"Next House Cost: ${house_cost}" if house_cost else "Next House Cost: N/A")
        lines.append(f"Hotel Cost: ${hotel_cost}" if hotel_cost else "Hotel Cost: N/A")
        return lines

    def draw_hover_tooltip(self, mouse_pos):
        if self.hovered_position is None:
            return
        space = board_spaces[self.hovered_position]
        lines = [space["name"]]
        if "property" in space:
            prop = space["property"]
            lines = self.get_property_tooltip_lines(prop)
        else:
            lines.append(f"Type: {space['type']}")
        padding = 8
        line_height = 20
        width = max(self.font.size(line)[0] for line in lines) + padding * 2
        height = line_height * len(lines) + padding * 2
        tooltip_x = mouse_pos[0] + 14
        tooltip_y = mouse_pos[1] + 14
        if tooltip_x + width > SCREEN_WIDTH:
            tooltip_x = mouse_pos[0] - width - 14
        if tooltip_y + height > SCREEN_HEIGHT:
            tooltip_y = mouse_pos[1] - height - 14
        tooltip_rect = pygame.Rect(tooltip_x, tooltip_y, width, height)
        tip_bg   = DM_SURFACE  if self.dark_mode else CANADA_WHITE
        tip_bord = DM_BORDER   if self.dark_mode else BLACK
        tip_txt  = DM_TEXT     if self.dark_mode else BLACK
        pygame.draw.rect(self.screen, tip_bg,   tooltip_rect)
        pygame.draw.rect(self.screen, tip_bord, tooltip_rect, 2)
        for i, line in enumerate(lines):
            surf = self.font.render(line, True, tip_txt)
            self.screen.blit(surf, (tooltip_x + padding, tooltip_y + padding + i * line_height))

    def try_buy_house(self, player, prop):
        if prop is None or prop.owner != player:
            self.set_message("You can only build on your own properties.")
            return
        if not self.owns_color_set(player, prop):
            self.set_message("You need the full color set to build here.")
            return
        house_cost = prop.get_house_cost()
        if house_cost is None:
            self.set_message("Cannot build a house here.")
            return
        same_color_props = [p for p in [s.get("property") for s in board_spaces] if p and p.property_type == PropertyType.PROPERTY and p.color == prop.color]
        counts = [(5 if p.hotel else p.houses) for p in same_color_props]
        min_houses = min(counts) if counts else 0
        if (5 if prop.hotel else prop.houses) != min_houses:
            self.set_message("Must build evenly across the color set.")
            return
        if HOUSE_POOL <= 0:
            self.set_message("No houses available in the bank.")
            return
        if player.pay(house_cost):
            prop.build_house()
            self.set_message(f"Built a house on {prop.name} for ${house_cost}.")
        else:
            self.set_message("Not enough money to buy a house.")

    def try_buy_hotel(self, player, prop):
        if prop is None or prop.owner != player:
            self.set_message("You can only build on your own properties.")
            return
        if not self.owns_color_set(player, prop):
            self.set_message("You need the full color set to build here.")
            return
        hotel_cost = prop.get_hotel_cost()
        if hotel_cost is None:
            self.set_message("Need 4 houses before buying a hotel.")
            return
        if HOTEL_POOL <= 0:
            self.set_message("No hotels available in the bank.")
            return
        if player.pay(hotel_cost):
            prop.build_hotel()
            self.set_message(f"Built a hotel on {prop.name} for ${hotel_cost}.")
        else:
            self.set_message("Not enough money to buy a hotel.")

    def owns_color_set(self, player, prop):
        if prop.property_type != PropertyType.PROPERTY:
            return False
        same_color_props = [
            space["property"] for space in board_spaces
            if space.get("property") and space["property"].property_type == PropertyType.PROPERTY
            and space["property"].color == prop.color
        ]
        return same_color_props and all(p.owner == player for p in same_color_props)

    def open_trade(self):
        self.trade_active = True
        self.trade_stage = "select"
        self.trade_partner_index = None
        self.trade_offer_props = set()
        self.trade_request_props = set()
        self.trade_offer_cash = 0
        self.trade_request_cash = 0
        self.trade_dragging = None
        self.waiting_for_action = False

    def close_trade(self, message=None):
        if message:
            self.set_message(message)
        self.trade_active = False
        self.trade_partner_index = None
        self.trade_offer_props = set()
        self.trade_request_props = set()
        self.trade_offer_cash = 0
        self.trade_request_cash = 0
        self.trade_dragging = None
        self.trade_stage = "select"
        self.waiting_for_action = True

    def apply_trade(self, current_player, partner):
        if self.trade_offer_cash > current_player.money or self.trade_request_cash > partner.money:
            self.set_message("Trade failed: not enough cash.")
            return False
        if any(p.owner != current_player for p in self.trade_offer_props):
            self.set_message("Trade failed: you no longer own some offered properties.")
            return False
        if any(p.owner != partner for p in self.trade_request_props):
            self.set_message("Trade failed: partner no longer owns some requested properties.")
            return False
        current_player.money -= self.trade_offer_cash
        partner.money += self.trade_offer_cash
        partner.money -= self.trade_request_cash
        current_player.money += self.trade_request_cash
        for prop in list(self.trade_offer_props):
            prop.owner = partner
            if prop in current_player.properties:
                current_player.properties.remove(prop)
            if prop not in partner.properties:
                partner.properties.append(prop)
        for prop in list(self.trade_request_props):
            prop.owner = current_player
            if prop in partner.properties:
                partner.properties.remove(prop)
            if prop not in current_player.properties:
                current_player.properties.append(prop)
        return True
    
    def next_turn(self):
        # Apply market effects each turn
        apply_market_effects()

        # Fluctuate every property value by a random ±5% each turn
        for prop in properties:
            multiplier = random.uniform(0.95, 1.05)
            prop.stock_value = max(10, int(round(prop.stock_value * multiplier)))

        if hasattr(self, 'extra_turn') and self.extra_turn:
            self.extra_turn = False
            return
        if hasattr(self, 'lose_turn') and self.lose_turn:
            self.lose_turn = False
            self.current_player_index = (self.current_player_index + 1) % len(self.players)
            return
        if self.is_double and not self.dice.double_count >= 3:
            return
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
        self.dice_rolled = False

    def get_board_metrics(self):
        left = float(self.board_rect.left)
        top = float(self.board_rect.top)
        side = float(self.board_rect.width)
        corner = side * 0.135
        edge = (side - (2 * corner)) / 9.0
        right = left + side
        bottom = top + side
        return left, top, right, bottom, corner, edge

    def get_space_center(self, position):
        rect = self.get_space_rect(position)
        return rect.center

    def get_space_rect(self, position):
        left, top, right, bottom, corner, edge = self.get_board_metrics()
        if position == 0:
            x, y, w, h = left, bottom - corner, corner, corner
        elif 1 <= position <= 9:
            x, y, w, h = left + corner + (position - 1) * edge, bottom - corner, edge, corner
        elif position == 10:
            x, y, w, h = right - corner, bottom - corner, corner, corner
        elif 11 <= position <= 19:
            offset = position - 10
            x, y, w, h = right - corner, bottom - corner - offset * edge, corner, edge
        elif position == 20:
            x, y, w, h = right - corner, top, corner, corner
        elif 21 <= position <= 29:
            offset = position - 20
            x, y, w, h = right - corner - offset * edge, top, edge, corner
        elif position == 30:
            x, y, w, h = left, top, corner, corner
        else:
            offset = position - 31
            x, y, w, h = left, top + corner + offset * edge, corner, edge
        return pygame.Rect(int(round(x)), int(round(y)), int(round(w)), int(round(h)))

    def draw_space(self, position):
        space = board_spaces[position]
        rect = self.get_space_rect(position)
        dm = self.dark_mode
        sp_bg   = DM_SURFACE  if dm else CANADA_WHITE
        sp_bord = DM_BORDER   if dm else BLACK
        pygame.draw.rect(self.screen, sp_bg,   rect)
        pygame.draw.rect(self.screen, sp_bord, rect, 2)
        if 0 < position < 10:
            bar_rect = pygame.Rect(rect.x, rect.y, rect.width, 14)
        elif 10 < position < 20:
            bar_rect = pygame.Rect(rect.x, rect.y, 14, rect.height)
        elif 20 < position < 30:
            bar_rect = pygame.Rect(rect.x, rect.bottom - 14, rect.width, 14)
        elif 30 < position < 40:
            bar_rect = pygame.Rect(rect.right - 14, rect.y, 14, rect.height)
        else:
            bar_rect = None
        if bar_rect and space["type"] in [PropertyType.PROPERTY, PropertyType.TRAIN_STATION, PropertyType.UTILITY]:
            pygame.draw.rect(self.screen, space["color"], bar_rect)
            pygame.draw.rect(self.screen, BLACK, bar_rect, 1)
        # Coloured outline showing which player owns this space
        if "property" in space:
            prop = space["property"]
            if prop.owner is not None:
                pygame.draw.rect(self.screen, prop.owner.color, rect, 5)
            label = "HOTEL" if prop.hotel else (f"H{prop.houses}" if prop.houses > 0 else None)
            if label:
                tag = self.font.render(label, True, RED)
                self.screen.blit(tag, tag.get_rect(center=rect.center))

    def draw_player_circles(self):
        players_by_position = {}
        for player in self.players:
            # Use animated position if animation is in progress
            if player in self.player_animations:
                anim = self.player_animations[player]
                display_pos = anim["start_pos"]
            else:
                display_pos = player.position
            players_by_position.setdefault(display_pos, []).append(player)
        
        for position, players_on_space in players_by_position.items():
            center_x, center_y = self.get_space_center(position)
            count = len(players_on_space)
            for index, player in enumerate(players_on_space):
                if count == 1:
                    offset_x, offset_y = 0, 0
                else:
                    angle = (2 * math.pi * index) / count
                    offset_x, offset_y = math.cos(angle) * 12, math.sin(angle) * 12
                
                draw_x = int(center_x + offset_x)
                draw_y = int(center_y + offset_y)
                
                # Apply jump animation if active
                if player in self.player_animations:
                    anim = self.player_animations[player]
                    progress = anim["progress"] / float(self.animation_duration)
                    
                    # Interpolate position from start to end
                    start_center = self.get_space_center(anim["start_pos"])
                    end_center = self.get_space_center(anim["end_pos"])
                    
                    anim_x = start_center[0] + (end_center[0] - start_center[0]) * progress
                    anim_y = start_center[1] + (end_center[1] - start_center[1]) * progress
                    
                    # Add vertical jump using sine wave
                    jump_height = 30
                    jump_offset = -jump_height * math.sin(progress * math.pi)
                    
                    draw_x = int(anim_x + offset_x)
                    draw_y = int(anim_y + offset_y + jump_offset)
                
                pygame.draw.circle(self.screen, player.color, (draw_x, draw_y), 10)
                pygame.draw.circle(self.screen, BLACK, (draw_x, draw_y), 2)
    
    def update_animations(self):
        """Update all player movement animations."""
        for player in list(self.player_animations.keys()):
            anim = self.player_animations[player]
            anim["progress"] += 1
            
            if anim["progress"] >= self.animation_duration:
                # Animation complete
                del self.player_animations[player]
    
    def draw_board(self):
        mouse_pos = pygame.mouse.get_pos()
        self.hovered_position = self.get_hovered_position(mouse_pos)
        dm = self.dark_mode

        bg_col = DM_BG if dm else CANADA_WHITE
        board_bg = DM_SURFACE if dm else LIGHT_GRAY
        border_col = DM_BORDER if dm else BLACK

        pygame.draw.rect(self.screen, board_bg, self.board_rect)
        pygame.draw.rect(self.screen, border_col, self.board_rect, 2)
        _, _, _, _, corner, _ = self.get_board_metrics()
        center_rect = pygame.Rect(
            int(round(self.board_rect.left + corner)),
            int(round(self.board_rect.top + corner)),
            int(round(self.board_rect.width - 2 * corner)),
            int(round(self.board_rect.height - 2 * corner)),
        )
        pygame.draw.rect(self.screen, board_bg, center_rect)
        pygame.draw.rect(self.screen, border_col, center_rect, 2)
        for position in range(len(board_spaces)):
            self.draw_space(position)
        if self.board_overlay_image:
            self.screen.blit(self.board_overlay_image, self.board_rect.topleft)
        if self.hovered_position is not None:
            pygame.draw.rect(self.screen, GOLD, self.get_space_rect(self.hovered_position), 3)
        self.draw_player_circles()

        # Draw card deck in board center
        self.draw_center_card_deck()

        self.draw_hover_tooltip(mouse_pos)

        txt_col = DM_TEXT if dm else BLACK

        info_x = self.info_x
        info_y = self.info_y
        current_player = self.players[self.current_player_index]
        player_text = self.big_font.render(f"Current: {current_player.name}", True, current_player.color)
        self.screen.blit(player_text, (info_x, info_y))
        money_text = self.font.render(f"Money: ${current_player.money}", True, txt_col)
        self.screen.blit(money_text, (info_x, info_y + 40))

        dice_type_colors = {
            DiceType.REGULAR: SKY_BLUE,
            DiceType.STABLE: GREEN,
            DiceType.HIGH_EXPLOSIVE: RED,
        }
        dice_label_color = dice_type_colors.get(self.dice.dice_type, txt_col)
        dice_text = self.font.render(f"Dice: {self.dice.dice_type.value}", True, dice_label_color)
        dice_text_pos = (info_x, info_y + 70)
        dice_text_rect = dice_text.get_rect(topleft=dice_text_pos)
        self.screen.blit(dice_text, dice_text_pos)

        market_fx_rect = None

        # Show active market effects count
        if active_market_effects:
            eff_text = self.font.render(f"Market FX active: {len(active_market_effects)}", True, RED)
            market_fx_pos = (info_x, info_y + 95)
            market_fx_rect = eff_text.get_rect(topleft=market_fx_pos)
            self.screen.blit(eff_text, market_fx_pos)

        # ── Settings button ───────────────────────────────────────────────────
        settings_col = DM_SURFACE2 if dm else (80, 80, 80)
        stats_col = BLUE if self.probability_panel_open else GRAY
        pygame.draw.rect(self.screen, stats_col, self.stats_button, border_radius=6)
        pygame.draw.rect(self.screen, DM_BORDER if dm else BLACK, self.stats_button, 1, border_radius=6)
        stats_lbl = self.font.render("Stats", True, CANADA_WHITE)
        self.screen.blit(stats_lbl, stats_lbl.get_rect(center=self.stats_button.center))
        pygame.draw.rect(self.screen, settings_col, self.settings_button, border_radius=6)
        pygame.draw.rect(self.screen, DM_BORDER if dm else BLACK, self.settings_button, 1, border_radius=6)
        gear_lbl = self.font.render("⚙ Settings", True, DM_TEXT if dm else CANADA_WHITE)
        self.screen.blit(gear_lbl, gear_lbl.get_rect(center=self.settings_button.center))
        if self.settings_open:
            self.draw_settings_panel()

        pygame.draw.rect(self.screen, CANADA_RED, self.roll_button)
        self.screen.blit(self.font.render("Roll Dice", True, CANADA_WHITE), (self.roll_button.x + 30, self.roll_button.y + 10))
        pygame.draw.rect(self.screen, BLUE, self.dice_button)
        self.screen.blit(self.font.render("Change Dice", True, CANADA_WHITE), (self.dice_button.x + 20, self.dice_button.y + 10))
        pygame.draw.rect(self.screen, GRAY, self.trade_button)
        self.screen.blit(self.font.render("Trade", True, CANADA_WHITE), (self.trade_button.x + 45, self.trade_button.y + 10))
        pygame.draw.rect(self.screen, RED, self.bankrupt_button)
        self.screen.blit(self.font.render("Bankrupt", True, CANADA_WHITE), (self.bankrupt_button.x + 30, self.bankrupt_button.y + 10))

        if market_fx_rect and market_fx_rect.collidepoint(mouse_pos):
            fx_lines = ["Current Market FX:"]
            for effect in active_market_effects:
                action = effect.get("action", "")
                amount = effect.get("amount", 0)
                turns_left = effect.get("turns_left", 0)
                if action == "inflation":
                    label = f"Inflation: +{amount}% ({turns_left} turns left)"
                elif action == "market_drop":
                    label = f"Market Drop: -{amount}% ({turns_left} turns left)"
                else:
                    label = f"{action}: {amount}% ({turns_left} turns left)"
                fx_lines.append(label)

            tip_surfaces = [self.font.render(line, True, txt_col) for line in fx_lines]
            tip_w = max(s.get_width() for s in tip_surfaces) + 16
            tip_h = sum(s.get_height() for s in tip_surfaces) + 12
            tip_x = mouse_pos[0] + 12
            tip_y = mouse_pos[1] + 12
            if tip_x + tip_w > SCREEN_WIDTH - 10:
                tip_x = SCREEN_WIDTH - tip_w - 10
            if tip_y + tip_h > SCREEN_HEIGHT - 10:
                tip_y = SCREEN_HEIGHT - tip_h - 10

            tip_rect = pygame.Rect(tip_x, tip_y, tip_w, tip_h)
            tip_bg = DM_SURFACE2 if dm else LIGHT_GRAY
            pygame.draw.rect(self.screen, tip_bg, tip_rect, border_radius=8)
            pygame.draw.rect(self.screen, DM_BORDER if dm else BLACK, tip_rect, 2, border_radius=8)

            line_y = tip_y + 6
            for surf in tip_surfaces:
                self.screen.blit(surf, (tip_x + 8, line_y))
                line_y += surf.get_height()

        if self.probability_panel_open:
            expected_roll = self.get_expected_roll(self.dice.dice_type)
            roll_variance = self.get_roll_variance(self.dice.dice_type)
            expected_doubles = self.get_doubles_probability(self.dice.dice_type) * 100
            observed_avg = (self.roll_sum_total / self.roll_count) if self.roll_count else 0.0
            observed_doubles = (self.doubles_count / self.roll_count * 100) if self.roll_count else 0.0

            recent_text = ", ".join(str(x) for x in self.last_rolls[-6:]) if self.last_rolls else "None"

            top_visits = sorted(self.position_visit_counts.items(), key=lambda item: item[1], reverse=True)
            hot_spaces = [f"{board_spaces[idx]['name']} ({count})" for idx, count in top_visits if count > 0][:3]
            if not hot_spaces:
                hot_spaces = ["No landed spaces recorded yet"]

            stats_lines = [
                "Probability Panel",
                f"Rolls recorded: {self.roll_count}",
                f"Expected roll: {expected_roll:.2f}   Observed mean: {observed_avg:.2f}",
                f"Variance: {roll_variance:.2f}",
                f"Expected doubles: {expected_doubles:.1f}%   Observed doubles: {observed_doubles:.1f}%",
                f"Recent rolls: {recent_text}",
                "Most visited spaces:",
            ] + hot_spaces

            panel_w = 610
            panel_h = 26 + len(stats_lines) * 19
            panel_x = 36
            panel_y = SCREEN_HEIGHT - panel_h - 20
            panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
            panel_bg = DM_SURFACE2 if dm else LIGHT_GRAY
            pygame.draw.rect(self.screen, panel_bg, panel_rect, border_radius=8)
            pygame.draw.rect(self.screen, DM_BORDER if dm else BLACK, panel_rect, 2, border_radius=8)

            line_y = panel_y + 8
            for i, line in enumerate(stats_lines):
                line_col = GOLD if i == 0 else txt_col
                surf = self.font.render(line, True, line_col)
                self.screen.blit(surf, (panel_x + 10, line_y))
                line_y += 19

        if dice_text_rect.collidepoint(mouse_pos):
            if self.dice.dice_type == DiceType.REGULAR:
                dice_lines = [
                    "Regular Dice Stats:",
                    "Each die: 1-6 (16.7% each)",
                    "Totals: 2-12 bell curve",
                    "Most likely total: 7 (16.7%)",
                    "Doubles chance: 16.7%",
                ]
            elif self.dice.dice_type == DiceType.STABLE:
                dice_lines = [
                    "Stable Dice Stats:",
                    "Each die: 3 or 4 (50% each)",
                    "Totals: 6 (25%), 7 (50%), 8 (25%)",
                    "Expected total: 7",
                    "Doubles chance: 50%",
                ]
            else:
                dice_lines = [
                    "High Explosive Dice Stats:",
                    "Each die: 1 or 6 (50% each)",
                    "Totals: 2 (25%), 7 (50%), 12 (25%)",
                    "Expected total: 7",
                    "Doubles chance: 50%",
                ]

            dice_tip_surfaces = [self.font.render(line, True, txt_col) for line in dice_lines]
            dice_tip_w = max(s.get_width() for s in dice_tip_surfaces) + 16
            dice_tip_h = sum(s.get_height() for s in dice_tip_surfaces) + 12
            dice_tip_x = mouse_pos[0] + 12
            dice_tip_y = mouse_pos[1] + 12
            if dice_tip_x + dice_tip_w > SCREEN_WIDTH - 10:
                dice_tip_x = SCREEN_WIDTH - dice_tip_w - 10
            if dice_tip_y + dice_tip_h > SCREEN_HEIGHT - 10:
                dice_tip_y = SCREEN_HEIGHT - dice_tip_h - 10

            dice_tip_rect = pygame.Rect(dice_tip_x, dice_tip_y, dice_tip_w, dice_tip_h)
            dice_tip_bg = DM_SURFACE2 if dm else LIGHT_GRAY
            pygame.draw.rect(self.screen, dice_tip_bg, dice_tip_rect, border_radius=8)
            pygame.draw.rect(self.screen, DM_BORDER if dm else BLACK, dice_tip_rect, 2, border_radius=8)

            dice_line_y = dice_tip_y + 6
            for surf in dice_tip_surfaces:
                self.screen.blit(surf, (dice_tip_x + 8, dice_line_y))
                dice_line_y += surf.get_height()

        if self.pending_property:
            pygame.draw.rect(self.screen, GREEN, self.buy_button)
            self.screen.blit(self.font.render("Buy Property", True, CANADA_WHITE), (self.buy_button.x + 18, self.buy_button.y + 10))
            pygame.draw.rect(self.screen, GRAY, self.skip_button)
            self.screen.blit(self.font.render("Skip", True, CANADA_WHITE), (self.skip_button.x + 52, self.skip_button.y + 10))
            pygame.draw.rect(self.screen, ORANGE, self.auction_button)
            self.screen.blit(self.font.render("Auction", True, CANADA_WHITE), (self.auction_button.x + 38, self.auction_button.y + 10))

        hovered_prop = self.get_hovered_property()
        can_manage_prop = hovered_prop and hovered_prop.owner == current_player and self.waiting_for_action and not self.dice_rolled and not self.pending_property
        can_build_now = can_manage_prop and self.owns_color_set(current_player, hovered_prop)

        if can_build_now:
            pygame.draw.rect(self.screen, ORANGE, self.house_button)
            house_cost = hovered_prop.get_house_cost()
            house_label = f"Buy House ${house_cost}" if house_cost else "Buy House"
            self.screen.blit(self.font.render(house_label, True, CANADA_WHITE), (self.house_button.x + 8, self.house_button.y + 10))
            pygame.draw.rect(self.screen, BROWN, self.hotel_button)
            hotel_cost = hovered_prop.get_hotel_cost()
            hotel_label = f"Buy Hotel ${hotel_cost}" if hotel_cost else "Buy Hotel"
            self.screen.blit(self.font.render(hotel_label, True, CANADA_WHITE), (self.hotel_button.x + 8, self.hotel_button.y + 10))

        if can_manage_prop:
            pygame.draw.rect(self.screen, GRAY, self.sell_house_button)
            self.screen.blit(self.font.render("Sell House/Hotel", True, CANADA_WHITE), (self.sell_house_button.x + 8, self.sell_house_button.y + 8))
            pygame.draw.rect(self.screen, GRAY, self.sell_property_button)
            self.screen.blit(self.font.render("Sell Property", True, CANADA_WHITE), (self.sell_property_button.x + 18, self.sell_property_button.y + 8))
            pygame.draw.rect(self.screen, GRAY, self.mortgage_button)
            self.screen.blit(self.font.render("Mortgage/Unmortgage", True, CANADA_WHITE), (self.mortgage_button.x + 6, self.mortgage_button.y + 8))

        if self.dice_rolled:
            roll_surface = self.big_font.render(f"Roll: {self.roll_value}", True, txt_col)
            roll_pos = (info_x, info_y + 230)
            self.screen.blit(roll_surface, roll_pos)

            die1, die2 = self.dice.roll_result
            dice_x = roll_pos[0] + roll_surface.get_width() + 14
            dice_y = roll_pos[1] - 4
            for idx, die_value in enumerate((die1, die2)):
                die_img = self.dice_face_images.get(die_value)
                draw_x = dice_x + idx * (self.dice_face_size + 8)
                if die_img:
                    self.screen.blit(die_img, (draw_x, dice_y))
                else:
                    fallback_rect = pygame.Rect(draw_x, dice_y, self.dice_face_size, self.dice_face_size)
                    pygame.draw.rect(self.screen, CANADA_WHITE, fallback_rect, border_radius=6)
                    pygame.draw.rect(self.screen, txt_col, fallback_rect, 2, border_radius=6)
                    num_surf = self.font.render(str(die_value), True, txt_col)
                    self.screen.blit(num_surf, num_surf.get_rect(center=fallback_rect.center))

            if self.is_double:
                self.screen.blit(self.font.render("DOUBLES!", True, RED), (info_x, info_y + 275))

        if self.pending_property:
            status_text = self.font.render("Status: Choose Buy or Skip", True, RED)
        elif self.auction_active:
            status_text = self.font.render("Status: Auction in progress", True, RED)
        elif self.hackathon_pending:
            status_text = self.font.render("Status: Choose Hackathon destination", True, BLUE)
        elif self.evaporator_pending:
            status_text = self.font.render("Status: Click property to evaporate house", True, BLUE)
        elif not self.dice_rolled:
            status_text = self.font.render("Status: Hover lot for info, then Click Roll Dice", True, txt_col)
        else:
            status_text = self.font.render("Status: Resolving turn...", True, txt_col)
        self.screen.blit(status_text, (info_x, info_y + 300))

        if self.message and self.message_timer > 0:
            # Draw notification below the chance card deck
            _, _, _, _, corner, _ = self.get_board_metrics()
            board_cx = self.board_rect.left + self.board_rect.width // 2
            board_cy = self.board_rect.top  + self.board_rect.height // 2
            card_bottom = board_cy + 63 + 4  # card_h//2 + stack offset
            notif_y = card_bottom + 14
            msg_surf = self.font.render(self.message, True, txt_col)
            msg_rect = msg_surf.get_rect(center=(board_cx, notif_y))
            pad_rect = msg_rect.inflate(24, 14)
            msg_bg = DM_SURFACE2 if dm else LIGHT_GRAY
            pygame.draw.rect(self.screen, msg_bg,  pad_rect, border_radius=8)
            pygame.draw.rect(self.screen, DM_BORDER if dm else BLACK, pad_rect, 2, border_radius=8)
            self.screen.blit(msg_surf, msg_rect)
            self.message_timer -= 1

        prop_y = info_y + 450
        if self.pending_property:
            prop_y = max(prop_y, self.auction_button.bottom + 20)
        if can_build_now:
            prop_y = max(prop_y, self.hotel_button.bottom + 20)
        elif can_manage_prop:
            prop_y = max(prop_y, self.mortgage_button.bottom + 20)

        available_h = max(0, self.trade_button.y - 10 - prop_y)
        max_entries = 0
        if available_h >= 45:
            max_entries = min(5, max(1, (available_h - 25) // 20))

        self.screen.blit(self.font.render("Your Properties:", True, txt_col), (info_x, prop_y))
        list_hover_prop = None
        for i, prop in enumerate(current_player.properties[:max_entries]):
            building_text = "H" + str(prop.houses) if prop.houses > 0 else ("HOTEL" if prop.hotel else "")
            prop_text = self.font.render(f"{prop.name} (${prop.stock_value}) {building_text}", True, prop.color)
            text_pos = (info_x, prop_y + 25 + i * 20)
            self.screen.blit(prop_text, text_pos)
            prop_rect = prop_text.get_rect(topleft=text_pos).inflate(6, 4)
            if prop_rect.collidepoint(mouse_pos):
                list_hover_prop = prop

        if list_hover_prop:
            lines = self.get_property_tooltip_lines(list_hover_prop)
            padding = 8
            line_height = 20
            width = max(self.font.size(line)[0] for line in lines) + padding * 2
            height = line_height * len(lines) + padding * 2
            tooltip_x = mouse_pos[0] + 14
            tooltip_y = mouse_pos[1] + 14
            if tooltip_x + width > SCREEN_WIDTH:
                tooltip_x = mouse_pos[0] - width - 14
            if tooltip_y + height > SCREEN_HEIGHT:
                tooltip_y = mouse_pos[1] - height - 14
            tooltip_rect = pygame.Rect(tooltip_x, tooltip_y, width, height)
            tip_bg = DM_SURFACE if self.dark_mode else CANADA_WHITE
            tip_bord = DM_BORDER if self.dark_mode else BLACK
            tip_txt = DM_TEXT if self.dark_mode else BLACK
            pygame.draw.rect(self.screen, tip_bg, tooltip_rect)
            pygame.draw.rect(self.screen, tip_bord, tooltip_rect, 2)
            for i, line in enumerate(lines):
                surf = self.font.render(line, True, tip_txt)
                self.screen.blit(surf, (tooltip_x + padding, tooltip_y + padding + i * line_height))

        # ── Hackathon Laptop UI ───────────────────────────────────────────────
        if self.hackathon_pending:
            popup_w, popup_h = 500, 160
            popup_x = (SCREEN_WIDTH - popup_w) // 2
            popup_y = (SCREEN_HEIGHT - popup_h) // 2
            popup_bg = DM_SURFACE if dm else CANADA_WHITE
            pygame.draw.rect(self.screen, popup_bg, (popup_x, popup_y, popup_w, popup_h))
            pygame.draw.rect(self.screen, DM_BORDER if dm else BLACK, (popup_x, popup_y, popup_w, popup_h), 2)
            self.screen.blit(self.big_font.render("Hackathon Laptop: Pick a number 1–12", True, txt_col), (popup_x + 15, popup_y + 12))
            self.hackathon_buttons = []
            for n in range(1, 13):
                col = (n - 1) % 6
                row = (n - 1) // 6
                btn_rect = pygame.Rect(popup_x + 20 + col * 75, popup_y + 60 + row * 50, 60, 36)
                pygame.draw.rect(self.screen, BLUE, btn_rect)
                lbl = self.font.render(str(n), True, CANADA_WHITE)
                self.screen.blit(lbl, lbl.get_rect(center=btn_rect.center))
                self.hackathon_buttons.append((btn_rect, n))

        # ── Evaporator UI ─────────────────────────────────────────────────────
        if self.evaporator_pending:
            buildable = [p for p in properties if (p.houses > 0 or p.hotel) and p.owner is not None]
            popup_w, popup_h = 500, min(400, 60 + len(buildable) * 36 + 20)
            popup_x = (SCREEN_WIDTH - popup_w) // 2
            popup_y = (SCREEN_HEIGHT - popup_h) // 2
            popup_bg = DM_SURFACE if dm else CANADA_WHITE
            pygame.draw.rect(self.screen, popup_bg, (popup_x, popup_y, popup_w, popup_h))
            pygame.draw.rect(self.screen, DM_BORDER if dm else BLACK, (popup_x, popup_y, popup_w, popup_h), 2)
            self.screen.blit(self.big_font.render("Evaporator: Pick property to remove house", True, txt_col), (popup_x + 10, popup_y + 10))
            self.evaporator_prop_rects = []
            for idx, prop in enumerate(buildable):
                btn_rect = pygame.Rect(popup_x + 20, popup_y + 50 + idx * 36, popup_w - 40, 30)
                pygame.draw.rect(self.screen, prop.color if prop.color != CANADA_WHITE else LIGHT_GRAY, btn_rect)
                building_str = "Hotel" if prop.hotel else f"{prop.houses} house(s)"
                lbl = self.font.render(f"{prop.name} [{building_str}] – owner: {prop.owner.name}", True, CANADA_WHITE if prop.color not in [CANADA_WHITE, YELLOW, GOLD] else BLACK)
                self.screen.blit(lbl, (btn_rect.x + 6, btn_rect.y + 6))
                self.evaporator_prop_rects.append((btn_rect, prop))

        if self.trade_active:
            popup_width = 720
            popup_height = 380
            popup_x = (SCREEN_WIDTH - popup_width) // 2
            popup_y = (SCREEN_HEIGHT - popup_height) // 2
            popup_rect = pygame.Rect(popup_x, popup_y, popup_width, popup_height)
            popup_bg = DM_SURFACE if dm else CANADA_WHITE
            popup_bord = DM_BORDER if dm else BLACK
            pygame.draw.rect(self.screen, popup_bg,   popup_rect)
            pygame.draw.rect(self.screen, popup_bord, popup_rect, 2)
            self.screen.blit(self.big_font.render("Trade", True, txt_col), (popup_x + 20, popup_y + 10))
            if self.trade_partner_index is None:
                self.screen.blit(self.font.render("Choose a player to trade with:", True, txt_col), (popup_x + 20, popup_y + 60))
                self.trade_partner_rects = []
                for i, player in enumerate(self.players):
                    if i == self.current_player_index:
                        continue
                    btn_rect = pygame.Rect(popup_x + 20, popup_y + 90 + len(self.trade_partner_rects) * 40, 240, 32)
                    pygame.draw.rect(self.screen, player.color, btn_rect)
                    self.screen.blit(self.font.render(player.name, True, CANADA_WHITE), (btn_rect.x + 10, btn_rect.y + 6))
                    self.trade_partner_rects.append((btn_rect, i))
            else:
                partner = self.players[self.trade_partner_index]
                left_x = popup_x + 20
                right_x = popup_x + 380
                list_top = popup_y + 70
                self.screen.blit(self.font.render(f"You: {current_player.name}", True, txt_col), (left_x, list_top))
                self.screen.blit(self.font.render(f"Partner: {partner.name}", True, txt_col), (right_x, list_top))
                self.trade_offer_prop_rects = []
                self.trade_request_prop_rects = []
                sel_col  = DM_SURFACE2 if dm else LIGHT_GRAY
                unsel_col = DM_SURFACE if dm else CANADA_WHITE
                for idx, prop in enumerate(current_player.properties):
                    row_y = list_top + 30 + idx * 24
                    row_rect = pygame.Rect(left_x, row_y, 320, 20)
                    selected = prop in self.trade_offer_props
                    pygame.draw.rect(self.screen, sel_col if selected else unsel_col, row_rect)
                    self.screen.blit(self.font.render(prop.name, True, prop.color), (row_rect.x + 4, row_rect.y + 2))
                    self.trade_offer_prop_rects.append((row_rect, prop))
                for idx, prop in enumerate(partner.properties):
                    row_y = list_top + 30 + idx * 24
                    row_rect = pygame.Rect(right_x, row_y, 320, 20)
                    selected = prop in self.trade_request_props
                    pygame.draw.rect(self.screen, sel_col if selected else unsel_col, row_rect)
                    self.screen.blit(self.font.render(prop.name, True, prop.color), (row_rect.x + 4, row_rect.y + 2))
                    self.trade_request_prop_rects.append((row_rect, prop))
                slider_y = popup_y + popup_height - 90
                slider_width = 260
                slider_height = 6
                offer_slider = pygame.Rect(left_x, slider_y, slider_width, slider_height)
                request_slider = pygame.Rect(right_x, slider_y, slider_width, slider_height)
                pygame.draw.rect(self.screen, GRAY, offer_slider)
                pygame.draw.rect(self.screen, GRAY, request_slider)
                offer_max = max(0, current_player.money)
                request_max = max(0, partner.money)
                offer_ratio = 0 if offer_max == 0 else self.trade_offer_cash / offer_max
                request_ratio = 0 if request_max == 0 else self.trade_request_cash / request_max
                offer_knob_x = offer_slider.x + int(offer_ratio * slider_width)
                request_knob_x = request_slider.x + int(request_ratio * slider_width)
                offer_knob = pygame.Rect(offer_knob_x - 6, slider_y - 6, 12, 18)
                request_knob = pygame.Rect(request_knob_x - 6, slider_y - 6, 12, 18)
                pygame.draw.rect(self.screen, BLUE, offer_knob)
                pygame.draw.rect(self.screen, BLUE, request_knob)
                self.screen.blit(self.font.render(f"You give: ${self.trade_offer_cash}", True, txt_col), (left_x, slider_y - 24))
                self.screen.blit(self.font.render(f"You get: ${self.trade_request_cash}", True, txt_col), (right_x, slider_y - 24))
                self.trade_offer_slider = offer_slider
                self.trade_request_slider = request_slider
                self.trade_offer_knob = offer_knob
                self.trade_request_knob = request_knob
                if self.trade_stage == "select":
                    self.trade_propose_button = pygame.Rect(popup_x + popup_width - 160, popup_y + popup_height - 50, 140, 32)
                    pygame.draw.rect(self.screen, GREEN, self.trade_propose_button)
                    self.screen.blit(self.font.render("Propose", True, CANADA_WHITE), (self.trade_propose_button.x + 28, self.trade_propose_button.y + 6))
                else:
                    self.trade_accept_button = pygame.Rect(popup_x + popup_width - 300, popup_y + popup_height - 50, 120, 32)
                    self.trade_decline_button = pygame.Rect(popup_x + popup_width - 160, popup_y + popup_height - 50, 120, 32)
                    pygame.draw.rect(self.screen, GREEN, self.trade_accept_button)
                    pygame.draw.rect(self.screen, RED, self.trade_decline_button)
                    self.screen.blit(self.font.render("Accept", True, CANADA_WHITE), (self.trade_accept_button.x + 22, self.trade_accept_button.y + 6))
                    self.screen.blit(self.font.render("Decline", True, CANADA_WHITE), (self.trade_decline_button.x + 18, self.trade_decline_button.y + 6))

        # ── Auction timer — top-right corner widget ──────────────────────────
        if self.auction_active:
            secs_left = max(0, math.ceil(self.auction_timer / FPS))
            total_secs = self.auction_turn_seconds
            ratio = self.auction_timer / max(1, total_secs * FPS)
            if ratio > 0.5:
                bar_color = GREEN
            elif ratio > 0.2:
                bar_color = ORANGE
            else:
                bar_color = RED

            tw, th = 160, 52
            tx = SCREEN_WIDTH - tw - 10
            ty = 10
            timer_bg = DM_SURFACE if dm else (240, 240, 240)
            timer_bord = DM_BORDER if dm else (80, 80, 80)
            pygame.draw.rect(self.screen, timer_bg,   (tx, ty, tw, th), border_radius=8)
            pygame.draw.rect(self.screen, bar_color,  (tx, ty, tw, th), 2, border_radius=8)

            label = self.font.render("Time to bid:", True, txt_col)
            self.screen.blit(label, (tx + 8, ty + 6))

            # Arc-style countdown bar
            bar_x, bar_y = tx + 8, ty + 28
            bar_w, bar_h = tw - 16, 12
            pygame.draw.rect(self.screen, timer_bord, (bar_x, bar_y, bar_w, bar_h), border_radius=5)
            filled_w = max(0, int(bar_w * ratio))
            if filled_w > 0:
                pygame.draw.rect(self.screen, bar_color, (bar_x, bar_y, filled_w, bar_h), border_radius=5)
            num = self.font.render(f"{secs_left}s", True, bar_color)
            self.screen.blit(num, (tx + tw - num.get_width() - 6, ty + 6))

        if self.auction_active:
            popup_width = 420
            popup_height = 200
            popup_x = (SCREEN_WIDTH - popup_width) // 2
            popup_y = (SCREEN_HEIGHT - popup_height) // 2
            popup_rect = pygame.Rect(popup_x, popup_y, popup_width, popup_height)
            popup_bg = DM_SURFACE if dm else CANADA_WHITE
            popup_bord = DM_BORDER if dm else BLACK
            pygame.draw.rect(self.screen, popup_bg,   popup_rect)
            pygame.draw.rect(self.screen, popup_bord, popup_rect, 2)
            current_bidder = self.get_current_auction_player()
            self.screen.blit(self.big_font.render("Auction", True, txt_col), (popup_x + 20, popup_y + 10))
            self.screen.blit(self.font.render(self.auction_property.name, True, txt_col), (popup_x + 20, popup_y + 50))
            self.screen.blit(self.font.render(f"Current bid: ${self.auction_current_bid}", True, txt_col), (popup_x + 20, popup_y + 75))
            if current_bidder:
                self.screen.blit(self.font.render(f"{current_bidder.name}'s turn (cash ${current_bidder.money})", True, txt_col), (popup_x + 20, popup_y + 100))

            # Tick the timer and end auction on expiry
            if self.auction_active:
                self.auction_timer -= 1
                if self.auction_timer <= 0:
                    self.finish_auction()

            self.raise_5_button   = pygame.Rect(popup_x + 20,  popup_y + 130, 90,  36)
            self.raise_20_button  = pygame.Rect(popup_x + 120, popup_y + 130, 90,  36)
            self.raise_100_button = pygame.Rect(popup_x + 220, popup_y + 130, 110, 36)
            self.leave_auction_button = pygame.Rect(popup_x + 340, popup_y + 130, 60, 36)
            pygame.draw.rect(self.screen, GREEN, self.raise_5_button)
            pygame.draw.rect(self.screen, GREEN, self.raise_20_button)
            pygame.draw.rect(self.screen, GREEN, self.raise_100_button)
            pygame.draw.rect(self.screen, GRAY,  self.leave_auction_button)
            self.screen.blit(self.font.render("+5",    True, CANADA_WHITE), (self.raise_5_button.x + 28,   self.raise_5_button.y + 8))
            self.screen.blit(self.font.render("+20",   True, CANADA_WHITE), (self.raise_20_button.x + 22,  self.raise_20_button.y + 8))
            self.screen.blit(self.font.render("+100",  True, CANADA_WHITE), (self.raise_100_button.x + 20, self.raise_100_button.y + 8))
            self.screen.blit(self.font.render("Leave", True, CANADA_WHITE), (self.leave_auction_button.x + 6, self.leave_auction_button.y + 8))
    
    def draw_center_card_deck(self):
        """Draw an animated card deck with CHANCE label in the board center."""
        dm = self.dark_mode
        _, _, _, _, corner, _ = self.get_board_metrics()
        cx = int(self.board_rect.left + corner + (self.board_rect.width  - 2*corner) / 2)
        cy = int(self.board_rect.top  + corner + (self.board_rect.height - 2*corner) / 2)

        card_w, card_h = 90, 126
        stack_offsets = [(4,4), (2,2), (0,0)]

        for ox, oy in stack_offsets:
            cr = pygame.Rect(cx - card_w//2 + ox, cy - card_h//2 + oy, card_w, card_h)
            back_col = (20, 60, 140) if not dm else (30, 80, 180)
            pygame.draw.rect(self.screen, back_col, cr, border_radius=8)
            # Subtle matching border — no gold
            pygame.draw.rect(self.screen, (40, 80, 160) if not dm else (50, 100, 200), cr, 2, border_radius=8)

        # Top card face
        face_r = pygame.Rect(cx - card_w//2, cy - card_h//2, card_w, card_h)
        face_col = (245, 245, 255) if not dm else (45, 45, 70)
        pygame.draw.rect(self.screen, face_col, face_r, border_radius=8)
        # Blue outline in dark mode, plain dark outline in light mode
        face_outline = (80, 160, 255) if dm else (60, 60, 120)
        pygame.draw.rect(self.screen, face_outline, face_r, 2, border_radius=8)

        # Inner decorative border — no gold
        inner = face_r.inflate(-10, -10)
        inner_border = (50, 130, 220) if dm else (80, 80, 160)
        pygame.draw.rect(self.screen, inner_border, inner, 1, border_radius=5)

        # "?" symbol
        futura_path = os.path.join("assets", "Futura.ttf")
        try:
            q_font = pygame.font.Font(futura_path, 52)
        except Exception:
            q_font = pygame.font.Font(None, 52)
        q_col = (220, 60, 60) if not dm else (255, 100, 100)
        q_surf = q_font.render("?", True, q_col)
        self.screen.blit(q_surf, q_surf.get_rect(center=(cx, cy - 18)))

        # "CHANCE" label
        futura_path = os.path.join("assets", "Futura.ttf")
        try:
            label_font = pygame.font.Font(futura_path, 20)
        except Exception:
            label_font = pygame.font.Font(None, 20)
        text_col = (40, 40, 100) if not dm else (180, 200, 255)
        lbl = label_font.render("CHANCE", True, text_col)
        self.screen.blit(lbl, lbl.get_rect(center=(cx, cy + 28)))

    def draw_settings_panel(self):
        """Draw the floating settings panel."""
        dm = self.dark_mode
        panel_w, panel_h = 260, 132
        panel_x = SCREEN_WIDTH - panel_w - 10
        panel_y = 48

        bg   = DM_SURFACE  if dm else CANADA_WHITE
        bord = DM_BORDER   if dm else BLACK
        txt  = DM_TEXT     if dm else BLACK

        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        pygame.draw.rect(self.screen, bg,   panel_rect, border_radius=8)
        pygame.draw.rect(self.screen, bord, panel_rect, 2, border_radius=8)

        title = self.font.render("⚙ Settings", True, txt)
        self.screen.blit(title, (panel_x + 12, panel_y + 10))

        # Dark mode toggle button
        dm_btn = pygame.Rect(panel_x + 12, panel_y + 42, panel_w - 24, 36)
        self.settings_darkmode_btn = dm_btn
        btn_col = (60, 100, 200) if dm else LIGHT_GRAY
        pygame.draw.rect(self.screen, btn_col, dm_btn, border_radius=6)
        pygame.draw.rect(self.screen, bord, dm_btn, 1, border_radius=6)

        toggle_label = "🌙  Dark Mode: ON" if dm else "☀  Dark Mode: OFF"
        lbl = self.font.render(toggle_label, True, DM_TEXT if dm else BLACK)
        self.screen.blit(lbl, lbl.get_rect(center=dm_btn.center))
        hint_lbl = self.font.render("P: Toggle Probability Panel", True, txt)
        self.screen.blit(hint_lbl, (panel_x + 12, panel_y + 88))

    def draw_game_over(self):
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        box_width, box_height = 400, 200
        box_x = (WIDTH - box_width) // 2
        box_y = (HEIGHT - box_height) // 2
        pygame.draw.rect(self.screen, CANADA_WHITE, (box_x, box_y, box_width, box_height))
        pygame.draw.rect(self.screen, CANADA_RED, (box_x, box_y, box_width, box_height), 3)
        winner_text = self.big_font.render(f"{self.winner.name} Wins!", True, CANADA_RED)
        self.screen.blit(winner_text, winner_text.get_rect(center=(WIDTH // 2, box_y + 60)))
        restart_button = pygame.Rect(box_x + 100, box_y + 120, 200, 50)
        pygame.draw.rect(self.screen, CANADA_RED, restart_button)
        restart_text = self.font.render("Restart Game", True, CANADA_WHITE)
        self.screen.blit(restart_text, restart_text.get_rect(center=restart_button.center))
        return restart_button
    
    def restart_game(self):
        self.game_over = False
        self.winner = None
        self.message = ""
        self.message_timer = 0
        self.waiting_for_action = True
        self.dice_rolled = False
        self.roll_value = 0
        self.is_double = False
        self.pending_property = None
        self.hovered_position = None
        self.auction_active = False
        self.auction_property = None
        self.auction_current_bid = 0
        self.auction_highest_bidder = None
        self.auction_turn_index = 0
        self.auction_active_players = []
        self.trade_active = False
        self.trade_stage = "select"
        self.trade_partner_index = None
        self.trade_offer_props = set()
        self.trade_request_props = set()
        self.trade_offer_cash = 0
        self.trade_request_cash = 0
        self.hackathon_pending = False
        self.hackathon_player = None
        self.evaporator_pending = False
        self.evaporator_player = None
        self.roll_count = 0
        self.roll_sum_total = 0
        self.doubles_count = 0
        self.roll_total_counts = {n: 0 for n in range(2, 13)}
        self.last_rolls = []
        self.position_visit_counts = {i: 0 for i in range(len(board_spaces))}
        active_market_effects.clear()
        for prop in properties:
            prop.owner = None
            prop.houses = 0
            prop.hotel = False
            prop.stock_value = prop.price
        self.players = []
        self.num_players = ask_player_count()
        self.setup_game()
        self.current_player_index = 0
    
    def run(self):
        running = True
        while running:
            if not self.game_over:
                self.force_bankruptcy_if_needed()
            
            # Update animations
            self.update_animations()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = pygame.mouse.get_pos()

                    if self.game_over:
                        box_width, box_height = 400, 200
                        box_x = (WIDTH - box_width) // 2
                        box_y = (HEIGHT - box_height) // 2
                        restart_button = pygame.Rect(box_x + 100, box_y + 120, 200, 50)
                        if restart_button.collidepoint(mouse_pos):
                            self.restart_game()
                        continue

                    # ── Hackathon Laptop pick ──────────────────────────────────
                    if self.hackathon_pending:
                        for btn_rect, n in self.hackathon_buttons:
                            if btn_rect.collidepoint(mouse_pos):
                                player = self.hackathon_player
                                player.position = n % len(board_spaces)
                                self.hackathon_pending = False
                                self.hackathon_player = None
                                self.waiting_for_action = True
                                self.set_message(f"Hackathon Laptop: moved to space {n}!")
                                self.handle_landing(player, player.position)
                                break
                        continue

                    # ── Evaporator pick ───────────────────────────────────────
                    if self.evaporator_pending:
                        for btn_rect, prop in self.evaporator_prop_rects:
                            if btn_rect.collidepoint(mouse_pos):
                                if prop.hotel:
                                    prop.hotel = False
                                    prop.houses = 0
                                    global HOTEL_POOL
                                    HOTEL_POOL += 1
                                    self.set_message(f"Evaporator destroyed the hotel on {prop.name}!")
                                elif prop.houses > 0:
                                    prop.houses -= 1
                                    global HOUSE_POOL
                                    HOUSE_POOL += 1
                                    self.set_message(f"Evaporator removed a house from {prop.name}!")
                                self.evaporator_pending = False
                                self.evaporator_player = None
                                self.waiting_for_action = True
                                break
                        continue

                    if self.trade_active:
                        if self.trade_partner_index is None:
                            for rect, idx in self.trade_partner_rects:
                                if rect.collidepoint(mouse_pos):
                                    self.trade_partner_index = idx
                                    self.trade_stage = "select"
                                    break
                            continue
                        partner = self.players[self.trade_partner_index]
                        if self.trade_stage == "select":
                            for rect, prop in self.trade_offer_prop_rects:
                                if rect.collidepoint(mouse_pos):
                                    if prop in self.trade_offer_props:
                                        self.trade_offer_props.remove(prop)
                                    else:
                                        self.trade_offer_props.add(prop)
                                    break
                            for rect, prop in self.trade_request_prop_rects:
                                if rect.collidepoint(mouse_pos):
                                    if prop in self.trade_request_props:
                                        self.trade_request_props.remove(prop)
                                    else:
                                        self.trade_request_props.add(prop)
                                    break
                            if self.trade_offer_knob.collidepoint(mouse_pos):
                                self.trade_dragging = "offer"
                            elif self.trade_request_knob.collidepoint(mouse_pos):
                                self.trade_dragging = "request"
                            if self.trade_propose_button.collidepoint(mouse_pos):
                                self.trade_stage = "confirm"
                            continue
                        if self.trade_stage == "confirm":
                            if self.trade_accept_button.collidepoint(mouse_pos):
                                success = self.apply_trade(self.players[self.current_player_index], partner)
                                self.close_trade("Trade completed." if success else "Trade failed.")
                            elif self.trade_decline_button.collidepoint(mouse_pos):
                                self.close_trade("Trade declined.")
                            continue

                    if self.auction_active:
                        current_bidder = self.get_current_auction_player()
                        if not current_bidder:
                            self.finish_auction()
                            continue
                        if self.leave_auction_button.collidepoint(mouse_pos):
                            self.auction_active_players = [p for p in self.auction_active_players if p != current_bidder]
                            self.advance_auction_turn()
                            continue
                        increment = None
                        if self.raise_5_button.collidepoint(mouse_pos):
                            increment = 5
                        elif self.raise_20_button.collidepoint(mouse_pos):
                            increment = 20
                        elif self.raise_100_button.collidepoint(mouse_pos):
                            increment = 100
                        if increment is not None:
                            new_bid = self.auction_current_bid + increment
                            if new_bid <= current_bidder.money:
                                self.auction_current_bid = new_bid
                                self.auction_highest_bidder = current_bidder
                                self.advance_auction_turn()
                            else:
                                self.set_message("You cannot bid more than your cash.")
                            continue

                    if self.pending_property:
                        player = self.players[self.current_player_index]
                        if self.buy_button.collidepoint(mouse_pos):
                            prop = self.pending_property
                            if player.pay(prop.price):
                                prop.owner = player
                                player.properties.append(prop)
                                self.set_message(f"Bought {prop.name} for ${prop.price}!")
                            else:
                                self.set_message("Not enough money. Starting auction.")
                                self.start_auction(prop)
                            self.pending_property = None
                            self.waiting_for_action = True
                            continue
                        if self.skip_button.collidepoint(mouse_pos):
                            self.set_message("Skipped property purchase.")
                            self.pending_property = None
                            self.waiting_for_action = True
                            continue
                        if self.auction_button.collidepoint(mouse_pos):
                            self.set_message(f"Starting auction for {self.pending_property.name}.")
                            self.start_auction(self.pending_property)
                            continue

                    hovered_prop = self.get_hovered_property()
                    player = self.players[self.current_player_index]
                    can_manage_prop = hovered_prop and hovered_prop.owner == player and self.waiting_for_action and not self.dice_rolled and not self.pending_property
                    if can_manage_prop:
                        if self.house_button.collidepoint(mouse_pos):
                            self.try_buy_house(player, hovered_prop)
                            continue
                        if self.hotel_button.collidepoint(mouse_pos):
                            self.try_buy_hotel(player, hovered_prop)
                            continue
                        if self.sell_house_button.collidepoint(mouse_pos):
                            gain = hovered_prop.sell_house()
                            if gain and gain > 0:
                                player.receive(gain)
                                self.set_message(f"Sold house/hotel on {hovered_prop.name} for ${gain}.")
                            else:
                                self.set_message("No houses or hotel to sell.")
                            continue
                        if self.sell_property_button.collidepoint(mouse_pos):
                            if hovered_prop.houses > 0 or hovered_prop.hotel:
                                self.set_message("Sell houses/hotel first before selling property.")
                                continue
                            if hovered_prop.mortgaged:
                                self.set_message("Cannot sell a mortgaged property. Unmortgage first.")
                                continue
                            amt = hovered_prop.sell_property_to_bank()
                            if amt is not None:
                                player.receive(amt)
                                if hovered_prop in player.properties:
                                    player.properties.remove(hovered_prop)
                                hovered_prop.owner = None
                                self.set_message(f"Sold {hovered_prop.name} to bank for ${amt}.")
                            continue
                        if self.mortgage_button.collidepoint(mouse_pos):
                            if hovered_prop.mortgaged:
                                cost = hovered_prop.get_unmortgage_cost()
                                if player.pay(cost):
                                    hovered_prop.unmortgage()
                                    self.set_message(f"Unmortgaged {hovered_prop.name} for ${cost}.")
                                else:
                                    self.set_message("Not enough money to unmortgage.")
                            else:
                                val = hovered_prop.mortgage()
                                if val is None:
                                    self.set_message("Cannot mortgage while houses or a hotel are present.")
                                else:
                                    player.receive(val)
                                    self.set_message(f"Mortgaged {hovered_prop.name} for ${val}.")
                            continue
                    
                    if self.roll_button.collidepoint(mouse_pos) and not self.dice_rolled and self.waiting_for_action:
                        player = self.players[self.current_player_index]
                        if player.in_jail:
                            if player.pay(50, None):
                                player.in_jail = False
                                player.jail_turns = 0
                                self.set_message("Paid $50 to fly back from the Arctic!")
                        else:
                            self.roll_value, self.is_double = self.dice.roll()
                            if player.next_roll_max_one:
                                self.roll_value = min(self.roll_value, 1)
                                self.is_double = False
                                player.next_roll_max_one = False
                            self.dice_rolled = True
                            if self.is_double:
                                player.consecutive_doubles += 1
                                if player.consecutive_doubles >= 3:
                                    player.position = 10
                                    player.in_jail = True
                                    player.consecutive_doubles = 0
                                    self.record_roll_stats(self.roll_value, self.is_double, player.position)
                                    self.set_message("Three doubles! Go to the Arctic!")
                                else:
                                    old_pos = player.position
                                    new_pos = player.move(self.roll_value)
                                    self.record_roll_stats(self.roll_value, self.is_double, new_pos)
                                    self.player_animations[player] = {
                                        "start_pos": old_pos,
                                        "end_pos": new_pos,
                                        "progress": 0
                                    }
                                    self.just_passed_go = new_pos < self.roll_value
                                    if self.just_passed_go:
                                        player.receive(200)
                                        self.set_message("Passed GO! Received $200")
                                    self.handle_landing(player, new_pos)
                            else:
                                player.consecutive_doubles = 0
                                old_pos = player.position
                                new_pos = player.move(self.roll_value)
                                self.record_roll_stats(self.roll_value, self.is_double, new_pos)
                                self.player_animations[player] = {
                                    "start_pos": old_pos,
                                    "end_pos": new_pos,
                                    "progress": 0
                                }
                                self.just_passed_go = new_pos < self.roll_value
                                if self.just_passed_go:
                                    player.receive(200)
                                    self.set_message("Passed GO! Received $200")
                                self.handle_landing(player, new_pos)
                    
                    if self.dice_button.collidepoint(mouse_pos) and self.waiting_for_action:
                        new_dice = self.dice.change_dice_type()
                        self.set_message(f"Dice changed to: {new_dice.value}", 120)

                    if self.trade_button.collidepoint(mouse_pos) and self.waiting_for_action and not self.dice_rolled:
                        self.open_trade()

                    if self.bankrupt_button.collidepoint(mouse_pos) and self.waiting_for_action:
                        current_player = self.players[self.current_player_index]
                        self.set_message(f"{current_player.name} declared bankruptcy.")
                        self.handle_bankruptcy(current_player)

                    # ── Settings button ───────────────────────────────────────
                    if self.stats_button.collidepoint(mouse_pos):
                        self.probability_panel_open = not self.probability_panel_open

                    if self.settings_button.collidepoint(mouse_pos):
                        self.settings_open = not self.settings_open

                    if self.settings_open and self.settings_darkmode_btn.collidepoint(mouse_pos):
                        self.dark_mode = not self.dark_mode

                elif event.type == pygame.MOUSEBUTTONUP:
                    if self.trade_dragging:
                        self.trade_dragging = None

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p:
                        self.probability_panel_open = not self.probability_panel_open

                elif event.type == pygame.MOUSEMOTION:
                    if self.trade_active and self.trade_dragging:
                        mouse_x = event.pos[0]
                        current_player = self.players[self.current_player_index]
                        if self.trade_partner_index is None:
                            continue
                        partner = self.players[self.trade_partner_index]
                        if self.trade_dragging == "offer":
                            slider = self.trade_offer_slider
                            relative = max(0, min(slider.width, mouse_x - slider.x))
                            max_cash = max(0, current_player.money)
                            self.trade_offer_cash = int(round((relative / slider.width) * max_cash)) if max_cash > 0 else 0
                        elif self.trade_dragging == "request":
                            slider = self.trade_request_slider
                            relative = max(0, min(slider.width, mouse_x - slider.x))
                            max_cash = max(0, partner.money)
                            self.trade_request_cash = int(round((relative / slider.width) * max_cash)) if max_cash > 0 else 0
            
            self.screen.fill(DM_BG if self.dark_mode else CANADA_WHITE)
            self.draw_board()
            
            if self.game_over:
                self.draw_game_over()
            
            if self.dice_rolled and self.waiting_for_action and self.message_timer <= 0:
                pygame.time.wait(1000)
                self.next_turn()
                self.dice_rolled = False
                self.waiting_for_action = True
            
            pygame.display.flip()
            self.clock.tick(FPS)
        
        pygame.quit()


def ask_player_count():
    while True:
        try:
            raw_value = input("How many players? (1-4): ").strip()
            num_players = int(raw_value)
            if 1 <= num_players <= 4:
                return num_players
            print("Please enter a number between 1 and 4.")
        except EOFError:
            return 2
        except ValueError:
            print("Please enter a valid whole number.")


if __name__ == "__main__":
    game = CanadaMonopoly(ask_player_count())
    game.run()
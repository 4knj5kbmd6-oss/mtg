"""Frank Karsten's Commander (99-card) numbers, for mana.py, from his TCGplayer articles "How Many Sources Do You Need
to Consistently Cast Your Spells? A 2022 Update" and "How Many Lands Do You Need in Your Deck? An Updated Analysis":
the land sources of a colour a cost needs, the land count, and the oracle-text rules for the cheap card draw and mana
ramp spells that lower it, matched without regard to case."""
import re

SOURCES = {  # (mana value, pips of the colour): sources needed, the 99-card column
    (1, 1): 19, (2, 1): 19, (3, 1): 18, (4, 1): 16, (5, 1): 15, (6, 1): 14,
    (2, 2): 30, (3, 2): 28, (4, 2): 26, (5, 2): 23, (6, 2): 22, (7, 2): 20,
    (3, 3): 36, (4, 3): 33, (5, 3): 30, (6, 3): 28, (7, 3): 26,
    (4, 4): 39, (5, 4): 36,
}
DRAW = ("draw a card", "draw two cards", "draw three cards", "draws cards", "draws two cards", "draws three cards")
DRAW_NOT = ("{4}", "Blood token", "investigate")
DRAW_CREATURE = ("when", "enters")
LOOK = ("look", "library", "put", "your hand")
LOOK_NOT = ("pay ", "pays")
CYCLES_FOR_ONE = re.compile(r"cycling \{[1WUBRGC]\}(?!\{)", re.I)
RAMP = ("add ",)
RAMP_NOT = ("add its ability", "add a lore counter")
RAMP_CREATURE_NOT = ("dies",)
SEARCH = ("search", "your library")
SEARCH_ANY = ("land", "basic")
SEARCH_NOT = ("sacrifice",)
AURA = ("enchanted land is tapped", "adds an additional")
CHEAT = ("put a creature card with", "from your hand onto the battlefield")


def sources(value, pips):
    """the sources a cost of this mana value with this many pips of a colour needs: off the table, the listed cost
    with the same pips, four at most, and the largest mana value not above it"""
    pips = min(pips, 4)
    return SOURCES[max(v for v, p in SOURCES if p == pips and v <= max(value, pips)), pips]


def cheap(value, text, creature):
    """whether a nonland card of this mana value, oracle text and type is a cheap card draw or mana ramp spell"""
    t = text.casefold()
    every = lambda *xs: all(x.casefold() in t for x in xs)
    some = lambda *xs: any(x.casefold() in t for x in xs)
    draw = (some(*DRAW) and not some(*DRAW_NOT) and (not creature or every(*DRAW_CREATURE))
            or not creature and every(*LOOK) and not some(*LOOK_NOT)
            or bool(CYCLES_FOR_ONE.search(text)))
    ramp = (some(*RAMP) and not some(*RAMP_NOT) and not (creature and some(*RAMP_CREATURE_NOT))
            or every(*SEARCH) and some(*SEARCH_ANY) and not some(*SEARCH_NOT)
            or every(*AURA) or every(*CHEAT))
    return value <= 2 and (draw or ramp)


def lands(mean, cheap):
    """the land count for this mean mana value of the nonland cards and count of cheap ones"""
    return 31.42 + 3.13 * mean - 0.28 * cheap

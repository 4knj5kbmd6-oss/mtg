"""Hypergeometric odds for mana.py, on the play in Commander: seven cards in hand and a draw every turn, turn one
included."""
from functools import cache
from itertools import product
from math import comb

CHOOSE = [[comb(n, k) for k in range(n + 1)] for n in range(128)]

def choose(n, k):
    """C(n, k), 0 outside 0 <= k <= n"""
    return 0 if k < 0 or k > n else CHOOSE[n][k] if n < len(CHOOSE) else comb(n, k)

def seen(turn):
    """the cards seen by this turn"""
    return 7 + turn

def at_least(want, hits, size, drawn):
    """the chance of at least want hits among drawn cards of a deck of size cards, hits of them hits"""
    return sum(comb(hits, k) * comb(size - hits, drawn - k) for k in range(want, drawn + 1)) / comb(size, drawn)

def given_lands(want, sources, lands, size, drawn, least):
    """the chance of at least want sources among drawn cards of a deck of size cards, lands of them lands and sources of
    those sources, given at least least lands among them; 0 when that many lands cannot be drawn"""
    ways = {k: comb(lands, k) * comb(size - lands, drawn - k) for k in range(least, min(drawn, lands) + 1)}
    total = sum(ways.values())
    return sum(w * at_least(want, sources, lands, k) for k, w in ways.items()) / total if total else 0.0

def supply(turn, size, drawn, lands, ramp, late):
    """[the chance of at least v mana on this turn, as mana() counts it, for v from 0 to drawn + 1]"""
    ways = [0] * (drawn + 2)
    for a in range(min(drawn, lands) + 1):
        for b in range(min(drawn - a, ramp) + 1):
            w = choose(lands, a) * choose(ramp, b) * choose(size - lands - ramp, drawn - a - b)
            m = min(a, turn) + b
            if late: ways[m - 1], ways[m] = ways[m - 1] + w * b, ways[m] + w * (drawn - b)
            else: ways[m] += w
    total, tail = choose(size, drawn) * (drawn if late else 1), 0
    for m in reversed(range(drawn + 2)): tail += ways[m]; ways[m] = tail / total
    return ways

def mana(want, turn, size, drawn, lands, ramp, late):
    """the chance of at least want mana on this turn from drawn cards of a deck of size cards, lands of them land drops
    played one a turn and ramp of them a mana each; when late, one of the drawn, at random, is this turn's draw, and as
    ramp it makes nothing yet"""
    chances = supply(turn, size, drawn, lands, ramp, late)
    return chances[want] if want < len(chances) else 0.0

def lands_seen(lands, size, drawn, least, deepest):
    """rows sigma from 0 to lands, columns j from 0 to deepest: the chance that the lands among drawn cards of a deck of
    size cards, lands of them lands, meet a given sigma of the lands in exactly a given j of them, given at least least
    lands among the drawn; None when that many lands cannot be drawn"""
    ways = {k: choose(lands, k) * choose(size - lands, drawn - k) for k in range(least, min(drawn, lands) + 1)}
    total = sum(ways.values())
    if not total: return None
    return [[sum(w * choose(lands - sigma, k - j) / choose(lands, k) for k, w in ways.items()) / total
             for j in range(deepest + 1)] for sigma in range(lands + 1)]

@cache
def terms(need):
    """the inclusion-exclusion terms of met() for this need: (sign, classes short, [(lands drawn of each, their sum)])"""
    out = []
    for mask in range(1 << len(need)):
        short = tuple(i for i in range(len(need)) if mask >> i & 1)
        picks = [(x, sum(x)) for x in product(*(range(need[i]) for i in short))]
        out.append((-1 if len(short) % 2 else 1, short, picks))
    return out

def met(counts, need, table):
    """the chance, from a lands_seen table, that the lands drawn hold at least need[i] of class i for every i, the
    classes disjoint and counts[i] lands each: the sum over each set of classes that fall short"""
    total = 0.0
    for sign, short, picks in terms(tuple(need)):
        row = table[sum(counts[i] for i in short)]
        part = 0.0
        for x, j in picks:
            ways = 1
            for i, n in zip(short, x): ways *= choose(counts[i], n)
            part += ways * row[j]
        total += sign * part
    return total

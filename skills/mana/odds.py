"""Hypergeometric odds for mana.py, on the play in Commander: seven cards in hand and a draw every turn, turn one
included."""
from math import comb

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

"""Hypergeometric odds for mana.py, on the play in Commander: seven cards in hand and a draw every turn, turn one
included."""
from math import comb

def seen(turn):
    """the cards seen by this turn"""
    return 7 + turn

def at_least(want, hits, size, drawn):
    """the chance of at least want hits among drawn cards of a deck of size cards, hits of them hits"""
    return sum(comb(hits, k) * comb(size - hits, drawn - k) for k in range(want, drawn + 1)) / comb(size, drawn)

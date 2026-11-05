"""A deck's recommended land count and its split among the identity's colours, for mana.py, from the deck's numbers
alone, as METHOD.md defines them."""
from collections import Counter
import odds

HORIZON = 10
EPS = 1e-9

def lands(size, spells, commanders, kept=0):
    """the fewest land drops, from 0 to size less the ramp and the kept, with the most weighted spells on time; None
    when size is below the cards seen by the horizon. spells: (weight, mana value, due turn, is ramp); commanders:
    (weight, mana value, due turn); kept: the cards held fixed beside the ramp that count for nothing"""
    if size < odds.seen(HORIZON): return None
    ramp = [mv for _, mv, _, is_ramp in spells if is_ramp]
    others = len(spells) - len(ramp)
    cards, led = Counter(), Counter()
    for w, mv, due, is_ramp in spells:
        if due <= HORIZON: cards[mv, due, is_ramp] += w
    for w, mv, due in commanders:
        if due <= HORIZON: led[mv, due] += w
    ready = [sum(r <= u - 1 for r in ramp) for u in range(HORIZON + 1)]

    def value(land):
        """the weighted spells on time with land land drops, the other spells filling the rest in the deck's proportions"""
        tables = {}
        def chance(want, turn, pool, drawn, ready_ramp, late):
            key = (turn, pool, drawn, ready_ramp, late)
            if key not in tables: tables[key] = odds.supply(turn, pool, drawn, land, ready_ramp, late)
            return tables[key][want] if want < len(tables[key]) else 0.0
        scale = (size - land - len(ramp) - kept) / others if others else 0.0
        total = 0.0
        for (mv, due, is_ramp), w in cards.items():
            if not (weight := w if is_ramp else w * scale): continue
            eligible = lambda u: ready[u] - (is_ramp and mv <= u - 1)
            on_time = (6 + due) * chance(mv, due, size - 1, 6 + due, eligible(due), True)
            on_time += sum(chance(mv, u, size - 1, 6 + u, eligible(u), False) for u in range(due, HORIZON + 1))
            total += weight * on_time / size
        for (mv, due), w in led.items():
            total += w * chance(mv, due, size, 7 + due, ready[due], True)
        return total

    values = [value(land) for land in range(size - len(ramp) - kept + 1)]
    return next(land for land, v in enumerate(values) if v >= max(values) - 1e-12)

def terms(lands, size, identity, spells, commanders, kept):
    """{pip vector, ((colour index, pips), ...): its cards' lands_seen tables, weighted and summed}"""
    ramp = sum(is_ramp for _, is_ramp, _, _ in spells)
    others = len(spells) - ramp
    scale = (size - lands - ramp - kept) / others if others else 0.0
    cards = [(w if is_ramp else w * scale, due, need, size - 1, 6 + due) for w, is_ramp, due, need in spells]
    cards += [(w, due, need, size, 7 + due) for w, due, need in commanders]
    deepest = max([sum(need.values()) for _, _, need, _, _ in cards] + [1])
    seen, merged = {}, {}
    for w, due, need, pool, drawn in cards:
        if not need: continue
        if (due, pool, drawn) not in seen: seen[due, pool, drawn] = odds.lands_seen(lands, pool, drawn, due, deepest)
        if (table := seen[due, pool, drawn]) is None: continue
        vector = tuple((identity.index(c), need[c]) for c in identity if c in need)
        into = merged.setdefault(vector, [[0.0] * (deepest + 1) for _ in range(lands + 1)])
        for row, add in zip(into, table):
            for j, x in enumerate(add): row[j] += w * x
    return merged

def worth(allocation, lands, size, identity, spells, commanders, kept=0):
    """the weighted cards whose pips are met on their due turn, given its lands, with allocation's sources of each
    colour among the lands. spells: (weight, is ramp, due turn, {colour: pips}); commanders: (weight, due turn,
    {colour: pips}); kept as in lands()"""
    return sum(odds.met([allocation[identity[i]] for i, _ in vector], [p for _, p in vector], table)
               for vector, table in terms(lands, size, identity, spells, commanders, kept).items())

def split(lands, size, identity, spells, commanders, kept=0):
    """{colour: sources}, summing to lands, with the most worth(), ties to the greatest in identity order"""
    m = len(identity)
    if m < 2: return dict.fromkeys(identity, lands)
    single, gold = [[0.0] * (lands + 1) for _ in identity], []
    for vector, table in terms(lands, size, identity, spells, commanders, kept).items():
        if len(vector) > 1: gold.append((vector, table)); continue
        (i, p), = vector
        for a in range(lands + 1): single[i][a] += odds.met([a], [p], table)
    # most[d][r]: the most the single-colour terms of colours d onward make of r lands
    most = [[0.0] * (lands + 1) for _ in identity] + [[0.0] + [float("-inf")] * lands]
    for d in reversed(range(m)):
        for r in range(lands + 1): most[d][r] = max(single[d][a] + most[d + 1][r - a] for a in range(r + 1))
    known = {}
    def pooled(prefix):
        """the gold terms with each one's colours past the prefix pooled into one class of the lands left: exact when
        the prefix covers its colours, and never below any completion"""
        d, left, total = len(prefix), lands - sum(prefix), 0.0
        for g, (vector, table) in enumerate(gold):
            counts = tuple(prefix[i] for i, _ in vector if i < d)
            rest = sum(p for i, p in vector if i >= d)
            if (key := (g, counts, left if rest else -1)) not in known:
                need = [p for i, p in vector if i < d] + [rest] * bool(rest)
                known[key] = odds.met([*counts, left][:len(need)], need, table)
            total += known[key]
        return total
    seed, left = [], lands
    for d in range(m - 1):
        seed.append(max(range(left + 1), key=lambda a: (single[d][a] + most[d + 1][left - a], a)))
        left -= seed[-1]
    seed.append(left)
    best = [seed, sum(single[d][a] for d, a in enumerate(seed)) + pooled(seed)]
    def search(prefix, sure):
        d, left = len(prefix), lands - sum(prefix)
        if d == m - 1:
            s, g = prefix + [left], sure + single[d][left] + pooled(prefix + [left])
            if g > best[1] + EPS or (g >= best[1] - EPS and s > best[0]): best[:] = [s, max(g, best[1])]
            return
        for a in sorted(range(left + 1), key=lambda a: (abs(a - seed[d]), -a)):
            here = sure + single[d][a]
            if here + most[d + 1][left - a] + pooled(prefix + [a]) >= best[1] - EPS: search(prefix + [a], here)
    search([], 0.0)
    return dict(zip(identity, best[0]))

def shares(sources):
    """{colour: percent}: each colour's sources in twentieths of the lands, rounded down, the twentieths left over to
    the largest remainders, ties in the dict's order, as multiples of 5"""
    lands = sum(sources.values())
    parts = {c: divmod(20 * s, lands) for c, s in sources.items()}
    up = sorted(parts, key=lambda c: -parts[c][1])[:20 - sum(u for u, _ in parts.values())]
    return {c: 5 * (u + (c in up)) for c, (u, _) in parts.items()}

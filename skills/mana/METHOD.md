# mana: method

How `mana.py` computes each number of `<run>/<slug>-mana.md`. C(n, k) is the
binomial coefficient, 0 outside 0 <= k <= n.

## The deck

Every count is over card copies of `list.txt`; a card `oracle.json` lacks is
left out.

| Term | Definition |
|---|---|
| N | The cards of the deck other than its commanders, 99 in a full deck |
| Commanders | The lines before the list's first blank line, always available from the command zone |
| Identity | The colours of the commanders' colour identity, in WUBRG order |
| Draws | A uniform shuffle of the N: positions 1 to 7 are the opening hand, position 7 + u is drawn on turn u, turn 1 included; no mulligan |
| Mana value, mv | The card's `cmc`, rounded down; a split, aftermath or Room card, whose `mana_cost` holds ` // `, takes its front half's cost instead, since its `cmc` sums both halves; adventure and modal double-faced cards keep their `cmc` |
| Pips of a colour | The `{W}` `{U}` `{B}` `{R}` `{G}` symbols of the front face's cost; hybrid and Phyrexian symbols are not counted |
| Due turn, t | max(1, mv, the card's pips summed over the colours) |
| Land drop | A card whose front face is a Land, or whose second face is a Land and whose front does not transform; a modal double-faced land is a land drop and its spell side is not counted |
| Ramp | A card that is not a land drop, read from its front face's text without reminder text: a permanent with a `{T}: Add` ability whose cost sacrifices nothing, or one that adds an additional mana, or a card that puts land cards from your library onto the battlefield without sacrificing a land. Each piece makes one mana a turn, from the turn after both its mv and the turn it was drawn |
| Not cast, X | The cards the plan's `- **Not cast:** Card; Card` line names, by name or either face. Each stays in the deck as a draw that occupies its slot, is neither land nor ramp and weighs 0 |
| Weight, w | The card's Score in the `## Cards` table of the deck's `nonlands.md`; the mean of the deck's scores for a card with none; 1 for every card when the deck has no scores |
| Land source of a colour | A land whose `produced_mana` holds it; a fetch land also makes the colours of the basic land types it searches for, and every colour of the identity when it searches for a basic land card of no type |

Lands play one a turn, so the lands in play on turn u are min(K, u), K the
land drops among the cards seen by turn u (7 + u of them).

## Curve, Lands and Colours

- **Curve:** Lands and Nonlands count front faces, commanders included; Not
  cast counts X; the curve buckets nonlands by mv, 7 and up together.
- **Lands:** the chance of at least k lands among the 7 + k cards seen by turn
  k, for k = 2, 3, 4, with ℓ the N's lands by front face:
  sum over j >= k of C(ℓ, j) C(N - ℓ, 7 + k - j) / C(N, 7 + k); `unknown` when
  N < 7 + k.
- **Sources needed:** a card with p pips of a colour, turn t' = min(mv, 7),
  seen n = 7 + t' cards and needing m = max(mv, p) lands, needs the fewest
  sources s of the ℓ lands with

      sum over k >= m of C(ℓ, k) C(N - ℓ, n - k) · P(at least p of s sources among k lands)
      ---------------------------------------------------------------------------------- >= 90%
                         sum over k >= m of C(ℓ, k) C(N - ℓ, n - k)

  The colour needs the most any of its cards needs (ties: the lower mv, then
  the name), X left out; Land sources, Nonland sources, Pips and the two pip
  columns count X. `-` when no s up to ℓ reaches 90%; `unknown` when N is below the
  cards seen by the turn of any of its cards.

## Land count

H = 10 turns, the game over which spells are valued, the same for every deck
so the count depends on the list alone. A cheap deck's own top of curve would
give it a short game and push its lands up.

A spell is on time when it is cast on its due turn, or on the turn it is
drawn if later, within H turns, with the mana there. The deck at L land drops
keeps its ramp R and its X, and its other M spells fill the N - L - R - X
slots left in the deck's proportions, each counting λ = (N - L - R - X) / M.

For a pool of S cards with ℓ land drops and e ramp that has come online, n of
them drawn, the chance of at least v mana on turn u is

    Q(v, u, S, n, ℓ, e, late) = sum over a, b of C(ℓ, a) C(e, b) C(S - ℓ - e, n - a - b) / C(S, n) · φ(a, b)
    φ(a, b) = 1 if min(a, u) + b >= v, else 0                                    (not late)
    φ(a, b) = (b / n) [min(a, u) + b - 1 >= v] + (1 - b / n) [min(a, u) + b >= v]  (late)

Late means one of the n, at random, is the turn's draw: a land drop there
counts, a ramp piece makes nothing yet. With e_u the ramp other than the card
whose mv <= u - 1, a card of the N with t <= H is on time with chance

    P = (1 / N) · [ (6 + t) · Q(mv, t, N - 1, 6 + t, L, e_t, late) + sum over u = t..H of Q(mv, u, N - 1, 6 + u, L, e_u, not late) ]

the first term for the 6 + t places before turn t's draw, the sum for each
turn u it may be drawn on. A commander's chance is Q(mv, t, N, 7 + t, L, e_t,
late). A card due after H is never on time.

    V(L) = sum over commanders of w P + sum over ramp of w P + λ · sum over other spells of w P

The recommended Lands is the fewest L from 0 to N - R - X with V(L) within
1e-12 of the most. Unknown when N < 7 + H.

The model's simplifications: each spell's mana is its own, not shared with
another cast that turn; ramp is castable on its turn; a spell that misses its
turn does not count later; every land makes every colour.

## Colour split

At the recommended L, each land makes one colour of the identity, s_c of
colour c, the s_c summing to L. The split is the s with the most

    G(s) = sum over cards with an identity pip of ω · P_c(s)

ω being w λ for other spells, w for ramp and commanders, 0 for X. P_c(s) is
the chance that the lands among the cards seen by the due turn meet every
colour's pips, given at least t of them are lands: a card of the N sees n =
6 + t of S = N - 1 others, a commander 7 + t of S = N. The land count k among
them has

    π(k) = C(L, k) C(S - L, n - k) / Z,  t <= k <= min(n, L),  Z the sum of those terms

and for the card's colours A with p_i pips each, by inclusion and exclusion
over the colours B that fall short:

    P_c(s) = sum over B ⊆ A of (-1)^|B| · sum over x_i < p_i (i in B) of [product over i in B of C(s_i, x_i)] · T(σ_B, |x|)
    T(σ, j) = sum over k of π(k) · C(L - σ, k - j) / C(L, k)

σ_B being the sum of s_i over B and |x| the sum of the x_i: x_i lands of each
colour of B and the rest of the k from lands of no colour of B.

A card with Z = 0 counts nothing. The search is exact: branch and bound over
the colours in identity order, the one-colour cards bounded by the best split
of the lands left among the colours left, each multicolour card by pooling
its unassigned colours into one class of the lands left. It returns the
argmax of G, ties to the greatest s in identity order. One colour takes every
land.

A real base meets the split when its lands match one to one the split's
sources, each land making its source's colour: true when every set of colours
has at least its sources' total among the lands making one of them. Every
card's chance on such a base is at least the split's.

## Shares

Each colour gets floor(20 s_c / L) twentieths, the twentieths left over going
to the largest remainders, ties in identity order; the share is 5 times its
twentieths, so the shares are multiples of 5 summing to 100.

## Recommendation table

| Column | What |
|---|---|
| Lands | The recommended L, then in brackets the band, every L from 0 to N - R - X with V(L) at least 99.5% of V at the recommended L, as `35 (33-37)`, the L alone when the band is that one count; `unknown` when N < 7 + H |
| Lands now | The N's land drops, X left out, modal lands included, so it compares with Lands, not with the Curve's Lands |
| One per colour | `share% (s_c)`; `-` when L is 0, `unknown` with Lands |
| Split now | Each colour's Land sources as shares of their sum over the identity, a land making two colours counted in both, rounded as the shares are: `colour share% (sources)`, joined by `, `; `-` with no land sources |

Sources needed and the split can disagree: Sources needed is the 90% bar for
the colour's most demanding card on any mix of lands, the split the most
weighted pips met across the whole deck at L lands, so a colour's hardest card
can need more sources than its share gives it.

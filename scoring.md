# Fit score

A 0 to 10 rating of a card's power in a specific deck. It is a power rating,
but power measured here, not in general: how much this card does for this
deck, at this deck's bracket, measured against the other 99 cards in it. Fit
is a large part of that, since a card that does not serve the plan has little
power in it, but a card that fits perfectly and does little is still weak.
The same card scores differently in different decks, and a format staple
earns nothing for its reputation.

## Anchors

| Score | Meaning |
|---|---|
| 10 | The most powerful card in the deck, or tied for it. The plan collapses or becomes a different deck without it. Commander-grade engines, the core combo piece, the best win condition. Rare: at most 3 to 5 per deck. |
| 9 | Core. An engine, enabler or finisher the deck is built to use, at full rate. Always glad to draw it. |
| 8 | Premium role player. Best-in-class at its job here (the top removal, the top ramp, the key tutor), or a second copy of a core effect. |
| 7 | Strong. Does its job efficiently and advances the plan. Survives any rebuild. |
| 6 | Good. Fits and pulls weight, but an equivalent card would do the same. |
| 5 | On the fence. Generic filler that fits the colours and curve. Take it or leave it. |
| 4 | Slightly below the line. Fine in a vacuum, but under rate for its role here, or the role is already saturated. First out when something better arrives. |
| 3 | Weak here. Off-plan, clunky, or outclassed by several cards already in the deck. Cut when convenient. |
| 2 | Poor. Rarely does anything useful in this deck. Cut. |
| 1 | Dead weight. Anti-synergy, wrong speed, or a plan the deck gave up on. Cut now. |
| 0 | Wrong. Illegal, colour-identity violation, or a card whose text actively hurts this deck. Immediate cut. |

## Rules of consistency

1. **Role first.** Name the card's job in this deck (ramp, draw, removal,
   engine, finisher, protection, fixing, tutor, utility). Judge rate and fit
   within that job: a 2-mana answer and a 5-mana answer to the same thing
   are not the same score.
2. **Power here, not in general.** How much does the card actually do in
   this deck's games: how often it matters, how much it swings when it does,
   how cheaply. A strong card that ignores the plan still does something; a
   weak card that fits the theme gets no credit for fitting. Neither has a
   fixed number: judge each on what it does here.
3. **The owner's plan comes first.** Read `decks/<slug>/plan.md` before scoring.
   It states the intended lines and the interactions the owner built the
   deck around, and it overrides any plan inferred from the list or from
   rankings.md. A card the plan names as part of a line is scored on that
   line, not on its face value.
4. **Saturation.** The 12th ramp piece in a deck that wants 10 loses a point
   or two; the 4th board wipe in a go-wide deck loses more.
5. **Bracket.** Score at the deck's bracket in rankings.md. A card that would
   push the deck up a bracket is scored as if it stayed, and flagged in the
   note instead.
6. **Mana base.** Basics are 5 unless the deck is mono-colour (then 6, they
   are the right card). Untapped duals and fetches 7 to 8; tapped duals 4 to 5;
   utility lands by what the ability does for this plan.
7. **Adds** are scored as if already in the deck, by the same anchors.
8. **Expected shape** of a reasonably tuned 100-card deck: around 3 cards at
   10, 8 to 12 at 8 or 9, the bulk between 5 and 7, and 8 to 15 at 4 or
   below. A deck that comes out with 30 cards at 8+ or none below 5 has been
   scored too generously; recheck.
9. **Note.** Every score carries a note of at most a dozen words naming the
   role and the reason. "Ramp, 2 mana, untapped: the best here" beats "good".

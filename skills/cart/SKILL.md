---
name: cart
description: Build and optimize a TCGplayer shopping cart from a card list (a deck, a set of tokens, a shopping list), balancing delivered price against package count, then audit it against the source list. Use when asked to build a cart, price a list, or buy cards on TCGplayer.
---

# cart

The cart is built in the built-in browser pane as a guest cart. Never sign
in, enter credentials or payment details, or check out: the owner does that.
Delegate the build to one `general-purpose` agent (`model` from
`output/settings.json`, default `claude-opus-5-5`, `run_in_background`)
with this file, the canonical list, the requirements (finish, condition,
language, artwork constraints, premium per package eliminated) and a
report path under `output/carts/<date>-<name>.md`. Ask the app
to keep the Mac awake (`request_keep_awake`, `session_idle`); a sleep
mid-run killed one build. Verify the live cart totals yourself before
reporting.

## 1. Requirements

Record before adding cards: source deck URL and included sections (main,
commander, sideboard, other); cards owned, with quantities; whether basics,
tokens and considering/maybeboard cards are excluded; finish (nonfoil, foil
or either); artwork and treatment (original art, regular frame, no
borderless or extended art); conditions and language (default English, Near
Mint to Moderately Played, never silently Heavily Played or Damaged); and
the priority (lowest delivered price, fewest packages, or a compromise with
a maximum premium for consolidation).

The deckbuilder's saved editions and finishes are arbitrary unless the buyer
says otherwise. Original artwork does not need the original edition: a
later reprint with the same art can be the better buy.

## 2. Canonical list

Read the actual source deck and take names and quantities from the requested
sections, with tokens and considering cards kept separate. Per card, buy
`max(0, deck quantity - owned)`, then apply the exclusions. Save the list
before shopping, with expected total copies, allowed extras labelled as
such, and printing exceptions to review: it is the source of truth for every
audit. "Buy what's pending" means every row of `output/changes.md` whose
Note says `unowned` (optionally for one deck), its In card at the count the
Note gives (`unowned, 10 copies`) or one copy, under the same rules as any
other list. Once the owner says the cart was bought, the orchestrator
clears `unowned` from those rows. Ignore display labels such as "Foil" or "Transform" and normalize
double-faced names when comparing. If the buyer changes the deck or
exclusions, update the list; never infer a card belongs because it is in the
cart or Saved for later.

## 3. Mass Entry

Open **Mass Entry**, select Magic: The Gathering, and set finish and
condition first. For nonfoil, leave **Normal** on and **Foil** off, and
recheck every time it opens: preferences reset. One line per card:
`1 Card Name`, `2 Card Name [SET]`, `1 Card Name [SET] 123`. Use names alone
when editions are flexible; add set and collector number only to pick
artwork or exclude a treatment, since locking every card to an edition
shrinks inventory and raises price and package count.

Import into an empty cart when possible; if it holds unrelated purchases,
keep and mark them rather than clearing it. Resolve every unmatched entry by
checking exact name, set code and collector number, not by guessing;
dropping a wrong collector number can help, but inspect the treatment it
lands on. Then run the audit checklist.

## 4. Optimizer before manual swaps

Record items, shipping, subtotal and package count; compare carts on items
plus shipping, before tax. For nonfoil, enable **Keep Current Printings** once
the cart is verified all nonfoil (it keeps finish, not artwork). Allow set
changes when editions are flexible, and preserve sets or set per-item rules
where an edition change could break artwork or treatment. The optimizer
matches by product name, so a set change can swap in a different card of the
same name (a 4/2 Beast for a 3/3): when names collide, whitelist set changes
per item. Keep conditions at the agreed minimum.

Try **Keep Current Sellers** first, then an unrestricted run if it is poor.
Tabulate the current cart, Direct, Verified Sellers and Any Seller by
required copies included, packages, items, shipping and delivered subtotal.
Direct is not automatically the best, and a cheaper result that omits cards
is not a result. Apply the best, then inspect the actual cart: applied
shipping and package count can differ from the quote, and allowed set
changes need artwork and treatment rechecked.

## 5. Manual swaps

Go after the largest avoidable costs: high-shipping packages, single-card
orders, two-card orders whose cards can both move to existing shipments,
expensive listings, and small buys that lift an order over a free-shipping
threshold. On a product page compare **Price + Shipping**, use **Sellers in
Cart** for overlap, and check each listing's finish (seller filters do not
exclude foils). A seller in the cart is a lead, not a shared package: it
may ship through Direct, and adding an item can change fulfillment.

A swap is worth `new subtotal - old subtotal`: price difference plus new
shipping minus shipping eliminated, with free-shipping thresholds counted
both ways. A slightly dearer card from an order already shipping free beats
a cheap one that opens a costly package. Move both cards of a two-card order
together, or its shipping stays.

1. Record the old listing's card, seller, finish, condition, quantity and price.
2. Confirm the replacement meets the requirements, add it, and see it in the cart.
3. Read and dismiss any regrouping notice.
4. Remove the old copy by seller and listing, not by card name; wait and
   verify the removal completed.
5. Check quantities, shipping, package count and total again.

Remove a whole seller package only when every card in it has a verified
replacement and it holds no unrelated purchases. Work in small batches: a
regrouping dialog can block queued removals and leave duplicates or
half-done swaps.

## 6. Regrouping

TCGplayer regroups to keep a seller's items together, so one new listing can
pull other cards out of Direct into a separately shipped package. After each
optimization or swap batch, read the notices, review new packages and high
shipping, recalculate the subtotal and check Saved for later. The cart's
applied shipping, not a product page's "Shipping included", is the real
cost. Keep a change only if its final price/package tradeoff is worth it;
correct or reverse an unexpected regroup before going on.

## 7. Dropped cards

Inventory moves mid-session. If items disappear, refresh the cart, compare
it with the canonical list (never the previous cart, which may hold
unrelated cards, earlier errors or unintended substitutions), use
availability alerts and Saved for later as clues, name the missing cards
exactly, restore only those with compliant listings, and rerun the audit.
Never "Add All" from Saved for later: it can hold unrelated purchases.

## Audit checklist

After the import, after any recovery, and on a refreshed cart just before
handing over. Against the canonical list, never an earlier cart; a matching
total is not enough, since a wrong extra can hide a missing card.

- Every required card at its quantity, after exclusions.
- No unintended extras, no duplicates from repeated imports.
- Required finish, language and an acceptable condition on every card.
- No prohibited full-art, extended-art, borderless or other treatment; any
  artwork deviation named.
- No required card in Saved for later.
- Shipping and package count acceptable; preorders and delays named.

## Report

Source deck, exclusions, required copies, missing / extras / wrong
quantities, finish and treatment exceptions, packages, item total, shipping,
subtotal before tax, preorders or delays, verification time; a screenshot of
the summary if useful. Stop when the cart is complete and compliant and
further consolidation costs more than the agreed premium; fewer packages is
not better if it materially raises the delivered price. State the final
tradeoff plainly, not as a global optimum. Inventory may still change: if
checkout reports changes, refresh and rerun the audit. Building the cart
does not authorize the order.

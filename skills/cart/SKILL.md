---
name: cart
description: Build and optimize a TCGplayer shopping cart from a card list (a deck, a set of tokens, a shopping list), balancing delivered price against package count, then audit it against the source list. Use when asked to build a cart, price a list, or buy cards on TCGplayer.
---

# cart

The cart is built in the built-in browser pane as a guest cart. Never sign
in, enter credentials or payment details, or check out: the owner does that.

1. **Requirements.** Record before adding cards: source deck URL and
   included sections (main, commander, sideboard, other); cards owned, with
   quantities; whether basics, tokens and considering/maybeboard cards are
   excluded; finish (nonfoil, foil or either); artwork and treatment
   (original art, regular frame, no borderless or extended art); conditions
   and language (default English, Near Mint to Moderately Played, never
   silently Heavily Played or Damaged); and the priority (lowest delivered
   price, fewest packages, or a compromise with a maximum premium per
   package eliminated).
2. **Canonical list.** Read the actual source deck and take names and
   quantities from the requested sections, with tokens and considering
   cards kept separate. Per card, buy `max(0, deck quantity - owned)`, then
   apply the exclusions. "Buy what's pending" means every row of
   `changes.md` whose Note says `unowned` (optionally for one deck),
   its In card at the count the Note gives (`unowned, 10 copies`) or one
   copy. Save the list in a scratchpad file before shopping, with expected
   total copies, allowed extras labelled as such, and printing exceptions to
   review. If the buyer changes the deck or exclusions, update the list.
3. Ask the app to keep the Mac awake (`request_keep_awake`, `session_idle`);
   a sleep mid-run kills a build.
4. Dispatch one `commander-deckhand:shopper`, `run_in_background` in the
   folder that holds `output/`, its prompt giving the canonical list's path,
   the requirements and the report path `output/carts/<date>-<name>.md`;
   `model` from `settings.json`, beside `output/`, is passed only when it
   differs from the default `claude-opus-5-5`, the agent's own.
5. Verify the live cart totals yourself before reporting. Once the owner
   says the cart was bought, clear `unowned` from the rows it bought.

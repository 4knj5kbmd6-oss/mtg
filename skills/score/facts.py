"""Write each deck's two fact files into <run_dir>: <slug>-combos.md, its combos from Commander Spellbook
(combos.py), and <slug>-mana.md, its mana from its list and oracle.json (mana.py).
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/score/facts.py <run_dir> <slug> [slug ...]
Prints the cards of each deck Spellbook or oracle.json does not know. When Spellbook is unreachable it prints one
line naming the URL, and the deck gets no combos file."""
import sys
import combos, mana

def main():
    if len(sys.argv) < 3: sys.exit(__doc__)
    run = sys.argv[1]
    for slug in sys.argv[2:]:
        combos.write(run, slug)
        mana.write(run, slug)

if __name__ == "__main__": main()

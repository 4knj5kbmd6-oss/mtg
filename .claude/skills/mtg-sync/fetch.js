// Run from any moxfield.com page. Paste the ids in (the keys of "decks" in decks/moxfield.json).
const ids = [/* "v156azYYskS5tYwPVChQyg", ... */];
const out = {};
for (const id of ids) {
  const d = await (await fetch(`https://api2.moxfield.com/v3/decks/all/${id}`)).json();
  const b = n => Object.values(d.boards?.[n]?.cards || {}).map(c => c.quantity + " " + c.card.name).sort((a, b) => a.slice(2).localeCompare(b.slice(2)));
  out[id] = { name: d.name, created: d.createdAtUtc, updated: d.lastUpdatedAtUtc,
    commanders: b('commanders'), mainboard: b('mainboard'), sideboard: b('sideboard'),
    tokens: (d.tokens || []).map(t => ({ name: t.name, set: t.set, cn: t.cn, colors: t.colors, pt: t.power != null ? t.power + "/" + t.toughness : "", type: t.type_line, text: (t.oracle_text || "").slice(0, 80) })) };
}
JSON.stringify(out)

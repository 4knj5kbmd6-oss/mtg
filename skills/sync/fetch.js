// Run from any moxfield.com page. Paste in the username and the ids (the keys of "decks" in output/decks/moxfield.json).
// Lists the user's decks, then fetches every id given and every public Commander deck listed. An answer that is not
// JSON (Cloudflare's challenge page, an error) comes back as {status, body} for sync.py to report.
const user = "";
const ids = [/* "v156azYYskS5tYwPVChQyg", ... */];
const get = async url => {
  try {
    const r = await fetch(url), body = await r.text();
    try { return JSON.parse(body); } catch { return { status: r.status, body: body.slice(0, 2000) }; }
  } catch (e) { return { status: 0, body: String(e) }; }
};
let listing = [];
for (let page = 1; ; page++) {
  const p = await get(`https://api2.moxfield.com/v2/decks/search?authorUserNames=${encodeURIComponent(user)}&pageNumber=${page}&pageSize=100&sortType=updated&sortDirection=descending`);
  if (!Array.isArray(p.data)) { listing = p; break; }
  listing.push(...p.data.map(({ publicId, name, format, visibility }) => ({ publicId, name, format, visibility })));
  if (page >= (p.totalPages || 1)) break;
}
const listed = Array.isArray(listing) ? listing.filter(d => d.visibility === "public" && /^commander/i.test(d.format)).map(d => d.publicId) : [];
const decks = {};
for (const id of new Set([...ids, ...listed])) {
  const d = await get(`https://api2.moxfield.com/v3/decks/all/${id}`);
  const b = n => Object.values(d.boards?.[n]?.cards || {}).map(c => c.quantity + " " + c.card.name).sort((a, b) => a.slice(2).localeCompare(b.slice(2)));
  decks[id] = !d.boards ? d : { name: d.name, created: d.createdAtUtc, updated: d.lastUpdatedAtUtc,
    commanders: b('commanders'), mainboard: b('mainboard'), sideboard: b('sideboard'),
    tokens: (d.tokens || []).map(t => ({ name: t.name, set: t.set, cn: t.cn, colors: t.colors, pt: t.power != null ? t.power + "/" + t.toughness : "", type: t.type_line, text: (t.oracle_text || "").slice(0, 80) })) };
}
JSON.stringify({ user, listing, decks })

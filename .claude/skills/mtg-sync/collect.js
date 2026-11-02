// Run on https://moxfield.com/users/<user> ("user" in decks/moxfield.json) after it renders.
const more = [...document.querySelectorAll('a,button')].find(e => /view more/i.test(e.textContent));
if (more) { more.click(); await new Promise(r => setTimeout(r, 4000)); }
[...new Set([...document.querySelectorAll('a[href^="/decks/"]')].map(a => a.getAttribute('href').split('/')[2]))].filter(id => !id.startsWith('public'))

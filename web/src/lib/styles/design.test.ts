import { readdirSync, readFileSync } from 'node:fs';
import { join, relative } from 'node:path';
import { describe, expect, it } from 'vitest';

// Controllo del design system: le regole sono in tokens.css, qui si vieta di aggirarle.
const SRC = join(process.cwd(), 'src');
const TOKENS = join(SRC, 'lib', 'styles', 'tokens.css');

const files = (readdirSync(SRC, { recursive: true }) as string[])
	.map((f) => join(SRC, f))
	.filter((f) => /\.(svelte|css|ts|html)$/.test(f) && !/\.test\.ts$/.test(f) && f !== TOKENS)
	.concat(join(SRC, 'app.html'));

type Hit = { at: string; text: string };
const rel = (f: string) => relative(process.cwd(), f).replaceAll('\\', '/');

/** Righe di CSS: file .css, blocchi <style> e attributi style="" dei .svelte e dell'html. */
function cssLines(f: string): { n: number; text: string }[] {
	const lines = readFileSync(f, 'utf8').split('\n');
	if (f.endsWith('.css')) return lines.map((text, i) => ({ n: i + 1, text }));
	if (f.endsWith('.ts')) return [];
	const out: { n: number; text: string }[] = [];
	let inStyle = false;
	lines.forEach((text, i) => {
		if (/<style\b/.test(text)) inStyle = true;
		if (inStyle) out.push({ n: i + 1, text });
		else for (const m of text.matchAll(/style="([^"]*)"/g)) out.push({ n: i + 1, text: m[1] });
		if (/<\/style>/.test(text)) inStyle = false;
	});
	return out;
}

function scan(pick: (text: string) => string | null, fromCss = true): Hit[] {
	const hits: Hit[] = [];
	for (const f of files) {
		const lines = fromCss
			? cssLines(f)
			: readFileSync(f, 'utf8')
					.split('\n')
					.map((text, i) => ({ n: i + 1, text }));
		for (const { n, text } of lines) {
			if (/^\s*@(media|container|supports)\b/.test(text)) continue;
			const found = pick(text);
			if (found) hits.push({ at: `${rel(f)}:${n}`, text: found });
		}
	}
	return hits;
}
const none = (hits: Hit[]) => expect(hits.map((h) => `${h.at}  ${h.text}`)).toEqual([]);

// Eccezione documentata in /admin/stile: la "G" ufficiale a colori richiesta dalle linee guida di Google.
const GOOGLE_LOGO = 'src/lib/components/GoogleLogo.svelte';
const GOOGLE_COLORS = ['#4285F4', '#34A853', '#FBBC05', '#EA4335'];

describe('design system', () => {
	it('spaziature, raggi e dimensioni solo da token (ammessi 0, 1px e 2px per i filetti)', () =>
		none(
			scan((t) => {
				const v = [...t.matchAll(/(?<![\w.#-])-?(?:\d*\.)?\d+(px|rem|em)\b/g)].map((m) => m[0]);
				const bad = v.filter((x) => !/^-?0(px|rem|em)$/.test(x) && x !== '1px' && x !== '2px');
				return bad.length ? bad.join(' ') : null;
			})
		));

	it('colori solo da token: niente esadecimali, rgb(), hsl() fuori da tokens.css', () =>
		none(
			scan(
				(t) =>
					!t.includes('theme-color') && // i meta del browser non leggono le variabili CSS
					/(?<![&\w])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b|\b(?:rgba?|hsla?|oklch|oklab)\(/.test(t)
						? t.trim()
						: null,
				false
			).filter((h) => !h.at.startsWith(GOOGLE_LOGO))
		));

	it('unica eccezione ai colori: la "G" di Google, con i quattro colori ufficiali e nient’altro', () => {
		const svg = readFileSync(join(process.cwd(), GOOGLE_LOGO), 'utf8');
		const used = [...svg.matchAll(/#[0-9a-fA-F]{6}\b/g)].map((m) => m[0].toUpperCase());
		expect(new Set(used)).toEqual(new Set(GOOGLE_COLORS));
	});

	it('font-weight solo 400 e 600', () =>
		none(
			scan((t) => {
				const w = t.match(/font-weight:\s*([^;}"]+)/)?.[1].trim();
				const s = t.match(/font:\s*(?:italic\s+)?(\d{3})\b/)?.[1];
				const v = w ?? s;
				return v && !['400', '600', 'var(--fw-regular)', 'var(--fw-strong)'].includes(v) ? t.trim() : null;
			})
		));

	it('niente maiuscolo forzato, gradienti, ombre colorate, filtri decorativi', () =>
		none(
			scan((t) => {
				if (/text-transform:\s*(uppercase|capitalize)/.test(t)) return t.trim();
				if (/(linear|radial|conic)-gradient/.test(t)) return t.trim();
				if (/text-shadow:|drop-shadow|backdrop-filter/.test(t)) return t.trim();
				const bs = t.match(/box-shadow:\s*([^;]+)/)?.[1].trim();
				if (bs && bs !== 'none' && bs !== 'var(--shadow-overlay)') return t.trim();
				return null;
			})
		));

	it('niente emoji nel codice', () =>
		none(scan((t) => (/\p{Extended_Pictographic}/u.test(t) ? t.trim() : null), false)));

	it('il rosso d’errore compare solo dove c’è sempre un’icona con il testo', () => {
		const allowed = ['src/app.css', 'src/lib/components/ErrorMessage.svelte'];
		none(
			scan((t) => (t.includes('var(--danger)') ? t.trim() : null), false).filter(
				(h) => !allowed.some((a) => h.at.startsWith(a))
			)
		);
	});
});

// --- Contrasto WCAG AA e distanza accento/errore, calcolati da tokens.css ---

const css = readFileSync(TOKENS, 'utf8');
const vars = Object.fromEntries([...css.matchAll(/(--[\w-]+):\s*([^;]+);/g)].map((m) => [m[1], m[2].trim()]));

function split(s: string): string[] {
	const out: string[] = [];
	let depth = 0;
	let cur = '';
	for (const ch of s) {
		if (ch === '(') depth++;
		if (ch === ')') depth--;
		if (ch === ',' && depth === 0) {
			out.push(cur.trim());
			cur = '';
		} else cur += ch;
	}
	return [...out, cur.trim()];
}
function resolve(v: string, theme: 0 | 1): string {
	const ld = v.match(/^light-dark\((.*)\)$/s);
	if (ld) return resolve(split(ld[1])[theme], theme);
	const ref = v.match(/^var\((--[\w-]+)\)$/);
	if (ref) return resolve(vars[ref[1]], theme);
	return v;
}
const lin = (c: number) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const rgb = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16) / 255);
const lum = (h: string) => {
	const [r, g, b] = rgb(h).map(lin);
	return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};
const ratio = (a: string, b: string) => {
	const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p);
	return (x + 0.05) / (y + 0.05);
};
const hue = (h: string) => {
	const [r, g, b] = rgb(h);
	const m = Math.max(r, g, b);
	const d = m - Math.min(r, g, b);
	const x = m === r ? ((g - b) / d) % 6 : m === g ? (b - r) / d + 2 : (r - g) / d + 4;
	return (x * 60 + 360) % 360;
};

describe.each([
	['chiaro', 0],
	['scuro', 1]
] as const)('contrasto, tema %s', (_name, theme) => {
	const c = (n: string) => resolve(`var(--${n})`, theme);
	const grounds = ['bg', 'surface', 'surface-2'];

	it.each(['text', 'muted', 'accent', 'danger'])('%s su bg, surface e surface-2 ≥ 4.5', (fg) => {
		for (const bg of grounds) expect(ratio(c(fg), c(bg)), `${fg} su ${bg}`).toBeGreaterThanOrEqual(4.5);
	});

	it('testo sul bottone primario ≥ 4.5', () =>
		expect(ratio(c('accent-ink'), c('accent'))).toBeGreaterThanOrEqual(4.5));

	it('bordo dei controlli ≥ 3 su bg e surface', () => {
		for (const bg of ['bg', 'surface']) expect(ratio(c('border-strong'), c(bg))).toBeGreaterThanOrEqual(3);
	});

	it('errore distinguibile dall’accento: tinta ad almeno 25° di distanza', () => {
		const d = Math.abs(hue(c('danger')) - hue(c('accent')));
		expect(Math.min(d, 360 - d)).toBeGreaterThanOrEqual(25);
	});
});

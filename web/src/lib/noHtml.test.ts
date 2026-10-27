import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const walk = (d: string): string[] =>
	readdirSync(d).flatMap((n) => (statSync(join(d, n)).isDirectory() ? walk(join(d, n)) : [join(d, n)]));

// Contenuti statici sicuri: path SVG fissi di Icon e JSON-LD (serializzato e con '<' escapato).
const ALLOWED = ['Icon.svelte', 'eventi/[slug]/+page.svelte'];

describe('sicurezza', () => {
	it('nessun {@html} con dati utente o evento', () => {
		const found = walk(join(process.cwd(), 'src'))
			.filter((f) => /\.svelte$/.test(f) && readFileSync(f, 'utf8').includes('{@html'))
			.filter((f) => !ALLOWED.some((a) => f.replaceAll('\\', '/').endsWith(a)));
		expect(found).toEqual([]);
	});
});

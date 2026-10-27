// Immagini di terze parti: srcset solo dove l'URL ha una scala Plone riconoscibile, altrimenti un solo src.

// Larghezze delle scale standard Plone (plone.app.imaging / Plone 6).
const PLONE_SCALES: Record<string, number> = {
	mini: 200,
	preview: 400,
	large: 800,
	larger: 1000,
	great: 1200,
	huge: 1600
};

// shortcut: gli URL Volto con hash (image-800-<hash>.jpeg) non si possono riscalare senza l'hash, restano un solo src.
const PLONE = /^(.*\/@@images\/image)\/(mini|preview|large|larger|great|huge)(\?.*)?$/;

export function imageSources(url: string): { src: string; srcset?: string } {
	const m = PLONE.exec(url);
	if (!m) return { src: url };
	const [, base, , qs = ''] = m;
	const srcset = Object.entries(PLONE_SCALES)
		.filter(([, w]) => w >= 400 && w <= 1200)
		.map(([name, w]) => `${base}/${name}${qs} ${w}w`)
		.join(', ');
	return { src: url, srcset };
}

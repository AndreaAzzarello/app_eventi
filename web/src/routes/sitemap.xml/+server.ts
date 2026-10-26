import { siteUrl } from '$lib/config';
import { cityPath, eventPath } from '$lib/event';
import { upcomingEvents } from '$lib/server/firestore';
import type { RequestHandler } from './$types';

// shortcut: un solo file con al massimo 2000 eventi futuri; oltre serve un indice di sitemap paginato.
const MAX_EVENTS = 2000;

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

export const GET: RequestHandler = async () => {
	const base = siteUrl();
	const events = await upcomingEvents(MAX_EVENTS);
	const cities = [...new Set(events.map((e) => e.citySlug).filter(Boolean))];
	const day = (ms?: number) => (ms ? `<lastmod>${new Date(ms).toISOString().slice(0, 10)}</lastmod>` : '');
	const urls = [
		`<url><loc>${base}/</loc><changefreq>daily</changefreq></url>`,
		...cities.map((c) => `<url><loc>${esc(base + cityPath(c))}</loc><changefreq>daily</changefreq></url>`),
		...events.map((e) => `<url><loc>${esc(base + eventPath(e))}</loc>${day(e.updatedAt ?? e.createdAt)}</url>`),
		`<url><loc>${base}/privacy</loc></url>`,
		`<url><loc>${base}/termini</loc></url>`
	];
	return new Response(
		`<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.join('\n')}\n</urlset>\n`,
		{
			headers: {
				'content-type': 'application/xml; charset=utf-8',
				'cache-control': 'public, max-age=3600, s-maxage=43200'
			}
		}
	);
};

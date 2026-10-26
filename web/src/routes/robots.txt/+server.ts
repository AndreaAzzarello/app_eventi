import { siteUrl } from '$lib/config';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = () =>
	new Response(
		[
			'User-agent: *',
			'Allow: /',
			'Disallow: /admin',
			'Disallow: /account',
			'Disallow: /accedi',
			'Disallow: /proponi',
			'Disallow: /preferiti',
			'Disallow: /api/',
			'',
			`Sitemap: ${siteUrl()}/sitemap.xml`,
			''
		].join('\n'),
		{ headers: { 'content-type': 'text/plain; charset=utf-8', 'cache-control': 'public, max-age=86400' } }
	);

import { HTML_CACHE } from '$lib/server/cache';
import { legalInfo } from '$lib/server/legal';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = ({ setHeaders }) => {
	setHeaders({ 'cache-control': HTML_CACHE });
	return legalInfo();
};

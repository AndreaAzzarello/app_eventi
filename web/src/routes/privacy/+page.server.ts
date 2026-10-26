import { legalInfo } from '$lib/server/legal';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = ({ setHeaders }) => {
	setHeaders({ 'cache-control': 'public, max-age=3600, s-maxage=86400' });
	return legalInfo();
};

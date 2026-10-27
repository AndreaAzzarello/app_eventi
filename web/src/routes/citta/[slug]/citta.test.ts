import { describe, expect, it, vi } from 'vitest';
import { fromData } from '$lib/event';

const calls: string[] = [];
const ev = (id: string, locality: string) =>
	fromData(id, { city: 'Terre del Reno', citySlug: 'terre-del-reno', province: 'FE', locality, startTime: 1 });
vi.mock('$lib/server/firestore', () => ({
	eventsInCity: async (slug: string) => (calls.push(slug), [ev('a', "Sant'Agostino"), ev('b', 'Mirabello')])
}));

describe('/citta/[slug]', () => {
	it('interroga per citySlug e titola col comune, non con la frazione', async () => {
		const { load } = await import('./+page.server');
		const r = (await load({ params: { slug: 'terre-del-reno' }, setHeaders() {} } as never)) as { city: string };
		expect(calls).toEqual(['terre-del-reno']);
		expect(r.city).toBe('Terre del Reno');
	});
});

import { windowRange, type DateWindow } from './dates';
import { CATEGORIES, compareEvents, isForKids, isFree, type Category, type Event } from './event';
import { DEFAULT_RADIUS_KM, RADII_KM, distanceKm, type LatLng } from './geo';

export interface Filter {
	q: string;
	when: DateWindow;
	free: boolean;
	kids: boolean;
	running: boolean;
	category: Category | null;
	radiusKm: number;
}

export const EMPTY_FILTER: Filter = {
	q: '',
	when: 'any',
	free: false,
	kids: false,
	running: false,
	category: null,
	radiusKm: DEFAULT_RADIUS_KM
};

/** I filtri vivono nell'URL (?q=&quando=&gratis=1&bambini=1&inCorso=1&cat=&r=): condivisibili e SSR. */
export function filterFromParams(p: URLSearchParams): Filter {
	const when = p.get('quando');
	const cat = p.get('cat');
	const r = Number(p.get('r'));
	return {
		q: (p.get('q') ?? '').slice(0, 100),
		when: when === 'oggi' ? 'today' : when === 'weekend' ? 'weekend' : 'any',
		free: p.get('gratis') === '1',
		// i vecchi link con cat=kids passano al filtro rapido, che include la categoria
		kids: p.get('bambini') === '1' || cat === 'kids',
		running: p.get('inCorso') === '1',
		category: cat && cat !== 'kids' && cat in CATEGORIES ? (cat as Category) : null,
		radiusKm: (RADII_KM as readonly number[]).includes(r) ? r : DEFAULT_RADIUS_KM
	};
}

export function filterToParams(f: Filter): URLSearchParams {
	const p = new URLSearchParams();
	if (f.q.trim()) p.set('q', f.q.trim());
	if (f.when !== 'any') p.set('quando', f.when === 'today' ? 'oggi' : 'weekend');
	if (f.free) p.set('gratis', '1');
	if (f.kids) p.set('bambini', '1');
	if (f.running) p.set('inCorso', '1');
	if (f.category) p.set('cat', f.category);
	if (f.radiusKm !== DEFAULT_RADIUS_KM) p.set('r', String(f.radiusKm));
	return p;
}

const norm = (s: string) =>
	s
		.normalize('NFD')
		.replace(/[̀-ͯ]/g, '')
		.toLowerCase();

/** Eventi non finiti che passano i filtri, ordinati per inizio. Come EventFilter.apply in Dart. */
export function applyFilter(events: Event[], f: Filter, now: number, origin: LatLng | null): Event[] {
	const range = windowRange(f.when, now);
	const q = norm(f.q.trim());
	return events
		.filter((e) => {
			if (e.endTime < now) return false;
			if (range && !(e.startTime < range[1] && e.endTime > range[0])) return false;
			if (f.free && !isFree(e)) return false;
			if (f.kids && !isForKids(e)) return false;
			if (f.running && !e.longRunning) return false;
			if (f.category && e.category !== f.category) return false;
			if (q && !norm(`${e.title} ${e.shortDescription} ${e.venueName} ${e.address} ${e.city}`).includes(q))
				return false;
			return !origin || distanceKm(origin, e) <= f.radiusKm;
		})
		.sort(compareEvents(now));
}

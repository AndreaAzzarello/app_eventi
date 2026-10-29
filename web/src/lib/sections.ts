import { romeParts, windowRange } from './dates';
import type { Event } from './event';

export type SectionKey = 'today' | 'tonight' | 'soon' | 'weekend' | 'later' | 'running';
export type Section = { key: SectionKey; title: string; events: Event[] };

/** Dalle 18 in poi un evento di oggi è "stasera". */
export const EVENING_HOUR = 18;

type Timed = Pick<Event, 'startTime' | 'endTime' | 'longRunning'>;

/**
 * Divide una lista (già filtrata e ordinata) in sezioni per tempo, in ora italiana. Ogni evento sta in una sola sezione;
 * l'ordine interno è quello ricevuto. Un evento già iniziato conta da adesso: una sagra iniziata ieri è "Oggi".
 * Mostre e rassegne lunghe (longRunning) vanno a parte, in "In corso", in fondo.
 */
export function sections<T extends Timed>(events: T[], now: number): { key: SectionKey; title: string; events: T[] }[] {
	const [dayStart, dayEnd] = windowRange('today', now)!;
	const [weekendStart, weekendEnd] = windowRange('weekend', now)!;
	const weekendNow = weekendStart <= dayStart; // sabato o domenica: il weekend è già qui
	const buckets: Record<SectionKey, T[]> = { today: [], tonight: [], soon: [], weekend: [], later: [], running: [] };

	for (const e of events) {
		const t = Math.max(e.startTime, now);
		let key: SectionKey;
		if (e.longRunning) key = 'running';
		else if (t < dayEnd) key = e.startTime >= dayStart && romeParts(e.startTime).hour >= EVENING_HOUR ? 'tonight' : 'today';
		else if (t >= weekendStart && t < weekendEnd) key = 'weekend';
		else if (t < weekendStart) key = 'soon';
		else key = 'later';
		buckets[key].push(e);
	}

	const titles: Record<SectionKey, string> = {
		today: 'Oggi',
		tonight: 'Stasera',
		soon: 'Prossimi giorni',
		weekend: 'Questo weekend',
		later: weekendNow ? 'Prossimi giorni' : 'Più avanti',
		running: 'In corso'
	};
	return (['today', 'tonight', 'soon', 'weekend', 'later', 'running'] as SectionKey[])
		.filter((key) => buckets[key].length)
		.map((key) => ({ key, title: titles[key], events: buckets[key] }));
}

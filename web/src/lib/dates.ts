// Date sempre in ora italiana, anche quando il server (Worker) gira in UTC.
export const TZ = 'Europe/Rome';

const partsFmt = new Intl.DateTimeFormat('en-US', {
	timeZone: TZ,
	year: 'numeric',
	month: 'numeric',
	day: 'numeric',
	hour: 'numeric',
	minute: 'numeric',
	second: 'numeric',
	hourCycle: 'h23',
	weekday: 'short'
});

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

/** Componenti della data in ora italiana. weekday: 0 = domenica. */
export function romeParts(ms: number) {
	const p = Object.fromEntries(partsFmt.formatToParts(ms).map((x) => [x.type, x.value]));
	return {
		year: +p.year,
		month: +p.month,
		day: +p.day,
		hour: +p.hour,
		minute: +p.minute,
		second: +p.second,
		weekday: WEEKDAYS.indexOf(p.weekday)
	};
}

/** Istante (ms) corrispondente a una data e ora "da muro" italiana. Regge l'ora legale. */
export function romeTime(year: number, month: number, day: number, hour = 0, minute = 0): number {
	const wall = Date.UTC(year, month - 1, day, hour, minute);
	let ms = wall;
	for (let i = 0; i < 2; i++) {
		const p = romeParts(ms);
		const seen = Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute, p.second);
		ms += wall - seen;
	}
	return ms;
}

export type DateWindow = 'any' | 'today' | 'weekend';

/** Intervallo [da, a) della finestra scelta, in ora italiana. */
export function windowRange(w: DateWindow, now: number): [number, number] | null {
	if (w === 'any') return null;
	const p = romeParts(now);
	if (w === 'today') return [romeTime(p.year, p.month, p.day), romeTime(p.year, p.month, p.day + 1)];
	// Di domenica il weekend in corso è iniziato ieri.
	const toSat = p.weekday === 0 ? -1 : 6 - p.weekday;
	return [romeTime(p.year, p.month, p.day + toSat), romeTime(p.year, p.month, p.day + toSat + 2)];
}

const dayFmt = new Intl.DateTimeFormat('it-IT', { timeZone: TZ, weekday: 'long', day: 'numeric', month: 'long' });
const dayYearFmt = new Intl.DateTimeFormat('it-IT', {
	timeZone: TZ,
	weekday: 'long',
	day: 'numeric',
	month: 'long',
	year: 'numeric'
});
const shortDayFmt = new Intl.DateTimeFormat('it-IT', { timeZone: TZ, day: 'numeric', month: 'short' });
/** "12 nov". */
export const shortDate = (ms: number) => shortDayFmt.format(ms);
const timeFmt = new Intl.DateTimeFormat('it-IT', { timeZone: TZ, hour: '2-digit', minute: '2-digit' });

const sameDay = (a: number, b: number) => {
	const x = romeParts(a);
	const y = romeParts(b);
	return x.year === y.year && x.month === y.month && x.day === y.day;
};
const allDay = (start: number, end: number) => {
	const s = romeParts(start);
	const e = romeParts(end);
	return s.hour === 0 && s.minute === 0 && e.hour === 23 && e.minute === 59;
};

/** "sabato 14 novembre · 21:00–23:30", "dal 12 nov al 15 nov". Anno solo se diverso da quello corrente. */
export function formatWhen(start: number, end: number, now = Date.now()): string {
	if (!sameDay(start, end)) return `dal ${shortDayFmt.format(start)} al ${shortDayFmt.format(end)}`;
	const day = (romeParts(start).year === romeParts(now).year ? dayFmt : dayYearFmt).format(start);
	if (allDay(start, end)) return `${day} · tutto il giorno`;
	const hours = end > start ? `${timeFmt.format(start)}–${timeFmt.format(end)}` : timeFmt.format(start);
	return `${day} · ${hours}`;
}

/** Etichetta corta per le card: "Oggi", "Domani", "sab 14 nov". */
export function shortDay(start: number, now = Date.now()): string {
	const start0 = Math.max(start, now);
	const p = romeParts(now);
	const tomorrow = romeTime(p.year, p.month, p.day + 1);
	if (sameDay(start0, now)) return 'Oggi';
	if (start0 >= tomorrow && start0 < romeTime(p.year, p.month, p.day + 2)) return 'Domani';
	return cardDayFmt.format(start0);
}
const cardDayFmt = new Intl.DateTimeFormat('it-IT', { timeZone: TZ, weekday: 'short', day: 'numeric', month: 'short' });

export const formatTime = (ms: number) => timeFmt.format(ms);

/** Valore per <input type="datetime-local"> in ora italiana, e ritorno. */
export function toLocalInput(ms: number): string {
	const p = romeParts(ms);
	const z = (n: number) => String(n).padStart(2, '0');
	return `${p.year}-${z(p.month)}-${z(p.day)}T${z(p.hour)}:${z(p.minute)}`;
}
export function fromLocalInput(v: string): number {
	const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(v);
	return m ? romeTime(+m[1], +m[2], +m[3], +m[4], +m[5]) : NaN;
}

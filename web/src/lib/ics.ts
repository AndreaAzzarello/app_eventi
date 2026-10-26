import type { Event } from './event';

const enc = new TextEncoder();

/** RFC 5545 §3.1: righe di al massimo 75 ottetti, le continuazioni iniziano con uno spazio. Non spezza i caratteri UTF-8. */
export function foldLine(line: string): string {
	const out: string[] = [];
	let cur = '';
	let bytes = 0;
	for (const ch of line) {
		const n = enc.encode(ch).length;
		const max = out.length ? 74 : 75; // lo spazio iniziale della continuazione conta
		if (bytes + n > max) {
			out.push(cur);
			cur = '';
			bytes = 0;
		}
		cur += ch;
		bytes += n;
	}
	out.push(cur);
	return out.join('\r\n ');
}

const esc = (s: string) =>
	s.replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\r?\n/g, '\\n');

const utc = (ms: number) => new Date(ms).toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');

/** File iCalendar con un solo evento. */
export function buildIcs(e: Event, url: string, now = Date.now()): string {
	const location = [e.venueName, e.address].filter(Boolean).join(', ');
	const description = [e.shortDescription, url].filter(Boolean).join('\n\n');
	return (
		[
			'BEGIN:VCALENDAR',
			'VERSION:2.0',
			'PRODID:-//Eventi Vicini//IT',
			'CALSCALE:GREGORIAN',
			'METHOD:PUBLISH',
			'BEGIN:VEVENT',
			`UID:${e.id}@eventi-vicini`,
			`DTSTAMP:${utc(now)}`,
			`DTSTART:${utc(e.startTime)}`,
			`DTEND:${utc(Math.max(e.endTime, e.startTime))}`,
			`SUMMARY:${esc(e.title)}`,
			description && `DESCRIPTION:${esc(description)}`,
			location && `LOCATION:${esc(location)}`,
			`GEO:${e.lat.toFixed(6)};${e.lng.toFixed(6)}`,
			`URL:${url}`,
			'END:VEVENT',
			'END:VCALENDAR'
		]
			.filter(Boolean)
			.map((l) => foldLine(l as string))
			.join('\r\n') + '\r\n'
	);
}

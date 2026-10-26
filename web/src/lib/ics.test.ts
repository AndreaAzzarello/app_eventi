import { describe, expect, it } from 'vitest';
import { fromData } from './event';
import { buildIcs, foldLine } from './ics';

const bytes = (s: string) => new TextEncoder().encode(s).length;
const unfold = (s: string) => s.split('\r\n').map((l, i) => (i ? l.slice(1) : l)).join('');

describe('foldLine (RFC 5545)', () => {
	it('righe corte intatte', () => expect(foldLine('SUMMARY:Ciao')).toBe('SUMMARY:Ciao'));
	it('spezza a 75 ottetti con spazio di continuazione', () => {
		const text = 'DESCRIPTION:' + 'a'.repeat(200);
		const lines = foldLine(text).split('\r\n');
		expect(lines.every((l) => bytes(l) <= 75)).toBe(true);
		expect(bytes(lines[0])).toBe(75);
		expect(lines.slice(1).every((l) => l.startsWith(' '))).toBe(true);
		expect(unfold(foldLine(text))).toBe(text);
	});
	it('non spezza i caratteri multibyte', () => {
		const text = 'DESCRIPTION:' + 'è€😀'.repeat(40);
		expect(foldLine(text).split('\r\n').every((l) => bytes(l) <= 75)).toBe(true);
		expect(unfold(foldLine(text))).toBe(text);
	});
});

describe('buildIcs', () => {
	const e = fromData('abc', {
		title: 'Concerto; jazz, blues',
		shortDescription: 'Riga 1\nRiga 2',
		startTime: Date.UTC(2026, 10, 14, 20),
		endTime: Date.UTC(2026, 10, 14, 22),
		venueName: 'Teatro',
		address: 'Via Roma 1, Modena',
		lat: 44.6,
		lng: 10.9
	});
	const ics = buildIcs(e, 'https://x.it/eventi/concerto-abc', Date.UTC(2026, 9, 1));
	it('struttura e CRLF', () => {
		expect(ics.startsWith('BEGIN:VCALENDAR\r\n')).toBe(true);
		expect(ics.endsWith('END:VCALENDAR\r\n')).toBe(true);
		expect(ics.replace(/\r\n/g, '')).not.toMatch(/\n/);
	});
	it('date UTC ed escape', () => {
		expect(ics).toContain('DTSTART:20261114T200000Z');
		expect(ics).toContain('DTEND:20261114T220000Z');
		expect(ics).toContain('SUMMARY:Concerto\\; jazz\\, blues');
		expect(ics).toContain('DESCRIPTION:Riga 1\\nRiga 2');
		expect(ics).toContain('UID:abc@eventi-vicini');
	});
});

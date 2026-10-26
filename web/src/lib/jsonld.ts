import { romeParts } from './dates';
import type { Event } from './event';

/** ISO 8601 con offset italiano (+01:00 / +02:00), come chiede schema.org. */
export function isoRome(ms: number): string {
	const p = romeParts(ms);
	const z = (n: number) => String(n).padStart(2, '0');
	const wall = Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute, p.second);
	const off = Math.round((wall - Math.floor(ms / 1000) * 1000) / 60000);
	const sign = off >= 0 ? '+' : '-';
	return `${p.year}-${z(p.month)}-${z(p.day)}T${z(p.hour)}:${z(p.minute)}:${z(p.second)}${sign}${z(Math.floor(Math.abs(off) / 60))}:${z(Math.abs(off) % 60)}`;
}

/** schema.org/Event. Mai submittedBy: chi propone resta anonimo. */
export function eventJsonLd(e: Event, url: string) {
	return {
		'@context': 'https://schema.org',
		'@type': 'Event',
		name: e.title,
		description: e.shortDescription || undefined,
		startDate: isoRome(e.startTime),
		endDate: isoRome(Math.max(e.endTime, e.startTime)),
		eventStatus: 'https://schema.org/EventScheduled',
		eventAttendanceMode: 'https://schema.org/OfflineEventAttendanceMode',
		url,
		image: e.imageUrl ? [e.imageUrl] : undefined,
		location: {
			'@type': 'Place',
			name: e.venueName || e.address,
			address: {
				'@type': 'PostalAddress',
				streetAddress: e.address,
				addressLocality: e.city || undefined,
				addressRegion: e.province || undefined,
				addressCountry: 'IT'
			},
			geo: { '@type': 'GeoCoordinates', latitude: e.lat, longitude: e.lng }
		},
		offers:
			e.ticketUrl || e.priceType === 'free'
				? {
						'@type': 'Offer',
						url: e.ticketUrl || url,
						...(e.priceType === 'free' ? { price: 0, priceCurrency: 'EUR' } : {}),
						availability: 'https://schema.org/InStock'
					}
				: undefined,
		isAccessibleForFree: e.priceType === 'free' ? true : undefined
	};
}

/** JSON sicuro dentro <script>: niente chiusura del tag né caratteri che rompono l'HTML. */
export const safeJson = (v: unknown) =>
	JSON.stringify(v).replace(/</g, '\\u003c').replace(/>/g, '\\u003e').replace(/&/g, '\\u0026');

import type { ChosenPlace } from './geo';
import { reversePlace } from './geocode';

/** Posizione del dispositivo, con "Vicino a <comune>" se il reverse geocoding risponde. Il messaggio dell'errore è per l'utente. */
export function locateMe(): Promise<ChosenPlace> {
	return new Promise((resolve, reject) => {
		if (!('geolocation' in navigator)) return reject(new Error('Il browser non supporta la geolocalizzazione.'));
		navigator.geolocation.getCurrentPosition(
			async ({ coords }) => {
				let label = 'La tua posizione';
				try {
					const hit = await reversePlace(coords.latitude, coords.longitude);
					if (hit?.place) label = `Vicino a ${hit.place.city}`;
				} catch {
					// etichetta generica: la posizione basta
				}
				resolve({ lat: coords.latitude, lng: coords.longitude, label });
			},
			(err) =>
				reject(
					new Error(
						err.code === err.PERMISSION_DENIED
							? 'Permesso negato. Puoi cercare la tua città nella barra di ricerca.'
							: 'Posizione non disponibile. Cerca la tua città nella barra di ricerca.'
					)
				),
			{ enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 }
		);
	});
}

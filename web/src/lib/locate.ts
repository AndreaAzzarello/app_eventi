import type { LatLng } from './geo';

/**
 * Posizione del dispositivo. Le coordinate non vanno a nessun servizio (niente reverse geocoding):
 * chi chiama le tiene nel browser e ne ricava, al più, il comune coperto più vicino. Il messaggio dell'errore è per l'utente.
 */
export function locateMe(): Promise<LatLng> {
	return new Promise((resolve, reject) => {
		if (!('geolocation' in navigator)) return reject(new Error('Il browser non supporta la geolocalizzazione.'));
		navigator.geolocation.getCurrentPosition(
			({ coords }) => resolve({ lat: coords.latitude, lng: coords.longitude }),
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

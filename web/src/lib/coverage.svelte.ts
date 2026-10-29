// Regioni e comuni coperti (da /api/places, in cache all'edge): caricati una volta, alla prima ricerca.
import type { CoverageRegion } from './places';

class CoverageStore {
	regions = $state.raw<CoverageRegion[]>([]);
	#pending: Promise<void> | null = null;

	/** Una sola richiesta alla volta; chi chiama può attendere che i dati siano arrivati. */
	load(): Promise<void> {
		if (this.regions.length) return Promise.resolve();
		return (this.#pending ??= this.#fetch().finally(() => (this.#pending = null)));
	}

	async #fetch() {
		try {
			const res = await fetch('/api/places');
			if (!res.ok) throw new Error(String(res.status));
			this.regions = await res.json();
		} catch {
			// la ricerca di località libere (Nominatim) funziona comunque; si riprova alla prossima occasione
		}
	}
}

export const coverageStore = new CoverageStore();

// Regioni e comuni coperti (da /api/places, in cache all'edge): caricati una volta, alla prima ricerca.
import type { CoverageRegion } from './places';

class CoverageStore {
	regions = $state.raw<CoverageRegion[]>([]);
	#loading = false;

	async load() {
		if (this.regions.length || this.#loading) return;
		this.#loading = true;
		try {
			const res = await fetch('/api/places');
			if (!res.ok) throw new Error(String(res.status));
			this.regions = await res.json();
		} catch {
			// la ricerca di località libere (Nominatim) funziona comunque; si riprova alla prossima occasione
		} finally {
			this.#loading = false;
		}
	}
}

export const coverageStore = new CoverageStore();

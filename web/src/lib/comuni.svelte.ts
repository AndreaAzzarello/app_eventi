// Tutti i comuni italiani per la ricerca: il file (~125 KB compressi, hash nel nome, cache immutabile) si scarica al primo
// uso della barra di ricerca, mai al caricamento della pagina. Si unisce alla copertura per sapere dove ci sono eventi.
import { decodeComuni, withCoverage, type Comune, type RawComuni } from './comuni';
import { coverageStore } from './coverage.svelte';

class ComuniStore {
	#list = $state.raw<Comune[]>([]);
	#pending: Promise<void> | null = null;
	/** Tutti i comuni con eventi e slug della copertura; vuoto finché il file non è arrivato (la ricerca usa allora la sola copertura). */
	index = $derived(withCoverage(this.#list, coverageStore.regions));

	/** Una sola richiesta alla volta; chi chiama può attendere che i dati siano arrivati. */
	load(): Promise<void> {
		if (this.#list.length) return Promise.resolve();
		return (this.#pending ??= import('./data/comuni.json')
			.then((m) => void (this.#list = decodeComuni(m.default as unknown as RawComuni)))
			.catch(() => undefined) // senza il file resta la ricerca nella copertura e su Nominatim; si riprova alla prossima occasione
			.finally(() => (this.#pending = null)));
	}
}

export const comuniStore = new ComuniStore();

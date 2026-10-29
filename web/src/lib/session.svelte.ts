// Stato di login e preferiti. Firebase parte solo se c'era già una sessione o se l'utente
// sceglie di accedere: il login non viene mai chiesto all'apertura.
import { ADMIN_EMAIL } from './config';
import { firebase, type Firebase } from './firebase/client';
import { KEYS, mergeFavorites, readJson, writeJson } from './storage';
import type { ChosenPlace } from './geo';
import { toast } from './toast.svelte';

export interface SessionUser {
	uid: string;
	email: string;
	name: string;
	isAdmin: boolean;
	provider: 'google' | 'email';
	lastSignIn: number;
}

class Session {
	user = $state<SessionUser | null>(null);
	/** idle: Firebase mai caricato (visitatore anonimo); ready: stato di login noto. */
	status = $state<'idle' | 'loading' | 'ready'>('idle');
	#started: Promise<Firebase> | null = null;

	/** Avvia Auth e ascolta i cambi di stato. Idempotente. */
	start(): Promise<Firebase> {
		this.#started ??= (async () => {
			this.status = 'loading';
			const fb = await firebase();
			await new Promise<void>((resolve) => {
				fb.a.onAuthStateChanged(fb.auth, async (u) => {
					if (u) {
						writeJson(KEYS.session, true);
						this.user = {
							uid: u.uid,
							email: u.email ?? '',
							name: u.displayName ?? '',
							isAdmin: u.email === ADMIN_EMAIL && u.emailVerified,
							provider: u.providerData.some((p) => p.providerId === 'google.com') ? 'google' : 'email',
							lastSignIn: Date.parse(u.metadata.lastSignInTime ?? '') || 0
						};
						try {
							const profile = await ensureProfile(fb, u.uid, u.displayName ?? '');
							await favorites.attach(fb, u.uid);
							await homePlace.attach(fb, u.uid, profile.homePlace);
						} catch (e) {
							console.error(e);
							toast('Non riesco a sincronizzare i preferiti: riprova più tardi.');
						}
					} else {
						writeJson(KEYS.session, null);
						this.user = null;
						favorites.detach();
						homePlace.detach();
					}
					this.status = 'ready';
					resolve();
				});
			});
			return fb;
		})();
		return this.#started;
	}

	/** All'avvio della pagina: carica Firebase solo per chi aveva già fatto login. */
	resume() {
		if (readJson(KEYS.session, false)) this.start();
		else this.status = 'ready';
	}

	async signOut() {
		const fb = await this.start();
		await fb.a.signOut(fb.auth);
	}
}

async function ensureProfile(fb: Firebase, uid: string, name: string): Promise<{ homePlace?: unknown }> {
	const ref = fb.fs.doc(fb.db, 'users', uid);
	const snap = await fb.fs.getDoc(ref);
	if (snap.exists()) return snap.data();
	await fb.fs.setDoc(ref, {
		name: name.slice(0, 80),
		city: '',
		createdAt: fb.fs.serverTimestamp(),
		pendingCount: 0
	});
	return {};
}

/** Solo i campi ammessi dalle regole (users/{uid}.homePlace), mai undefined; null se non è una zona valida. */
export function toHomePlace(p: unknown): ChosenPlace | null {
	const v = p as Partial<ChosenPlace> | null;
	if (!v || typeof v.label !== 'string' || !v.label || !Number.isFinite(v.lat) || !Number.isFinite(v.lng)) return null;
	return {
		label: v.label.slice(0, 80),
		lat: v.lat!,
		lng: v.lng!,
		...(v.slug ? { slug: v.slug.slice(0, 80) } : {}),
		...(v.region ? { region: v.region.slice(0, 80) } : {})
	};
}

/** Zona scelta: in localStorage per chi è anonimo, anche nel profilo (users/{uid}.homePlace) per chi ha l'account. */
class HomePlace {
	/** Impostata al login quando il profilo ha una zona: la home la applica. */
	value = $state<ChosenPlace | null>(null);
	#remote: { fb: Firebase; uid: string } | null = null;

	/** Al login: la zona del profilo vince e aggiorna quella locale; se il profilo non ne ha, vale quella locale. */
	async attach(fb: Firebase, uid: string, remote: unknown) {
		this.#remote = { fb, uid };
		const saved = toHomePlace(remote);
		if (saved) {
			writeJson(KEYS.place, saved);
			this.value = saved;
			return;
		}
		const local = toHomePlace(readJson<unknown>(KEYS.place, null));
		if (local) await this.#write(local);
	}

	detach() {
		this.#remote = null;
		this.value = null;
	}

	/** Dopo una scelta dell'utente: se ha l'account la salva nel profilo. */
	save(p: ChosenPlace) {
		const place = toHomePlace(p);
		if (place && this.#remote) this.#write(place).catch((e) => console.error(e));
	}

	async #write(place: ChosenPlace) {
		const { fb, uid } = this.#remote!;
		await fb.fs.updateDoc(fb.fs.doc(fb.db, 'users', uid), { homePlace: place });
	}
}

class Favorites {
	ids = $state<string[]>([]);
	#remote: { fb: Firebase; uid: string } | null = null;

	load() {
		if (!this.#remote) this.ids = readJson<string[]>(KEYS.favorites, []);
	}

	has(id: string) {
		return this.ids.includes(id);
	}

	/** Restituisce true se l'evento è stato aggiunto. */
	async toggle(id: string): Promise<boolean> {
		const adding = !this.has(id);
		const before = this.ids;
		this.ids = adding ? [...before, id] : before.filter((x) => x !== id);
		const remote = this.#remote;
		if (!remote) {
			writeJson(KEYS.favorites, this.ids);
			if (adding && !readJson(KEYS.loginHintShown, false)) {
				writeJson(KEYS.loginHintShown, true);
				toast('Salvato nei preferiti su questo dispositivo.', {
					label: 'Accedi per non perderli',
					href: `/accedi?next=${encodeURIComponent(location.pathname + location.search)}`
				}, 10000);
			}
			return adding;
		}
		const ref = remote.fb.fs.doc(remote.fb.db, 'users', remote.uid, 'favorites', id);
		try {
			if (adding) await remote.fb.fs.setDoc(ref, { addedAt: Date.now() });
			else await remote.fb.fs.deleteDoc(ref);
		} catch (e) {
			this.ids = before;
			throw e;
		}
		return adding;
	}

	/** Al login: unisce i preferiti locali a quelli dell'account e svuota la copia locale. */
	async attach(fb: Firebase, uid: string) {
		const { fs, db } = fb;
		const snap = await fs.getDocs(fs.collection(db, 'users', uid, 'favorites'));
		const { toUpload, merged } = mergeFavorites(
			readJson<string[]>(KEYS.favorites, []),
			snap.docs.map((d) => d.id)
		);
		if (toUpload.length) {
			const batch = fs.writeBatch(db);
			const now = Date.now();
			for (const id of toUpload.slice(0, 450)) batch.set(fs.doc(db, 'users', uid, 'favorites', id), { addedAt: now });
			await batch.commit();
		}
		writeJson(KEYS.favorites, null);
		this.#remote = { fb, uid };
		this.ids = merged;
	}

	detach() {
		this.#remote = null;
		this.ids = readJson<string[]>(KEYS.favorites, []);
	}
}

export const session = new Session();
export const favorites = new Favorites();
export const homePlace = new HomePlace();

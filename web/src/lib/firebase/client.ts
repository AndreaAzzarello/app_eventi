// Firebase si carica solo quando serve (login, preferiti sincronizzati, proposte, admin):
// chi naviga senza account non scarica l'SDK. Firestore "lite": niente realtime, bundle piccolo.
import { firebaseConfig, useEmulators } from '$lib/config';

let ready: Promise<Firebase> | null = null;

async function init() {
	const [{ initializeApp }, authMod, fsMod] = await Promise.all([
		import('firebase/app'),
		import('firebase/auth'),
		import('firebase/firestore/lite')
	]);
	const app = initializeApp(firebaseConfig());
	const auth = authMod.initializeAuth(app, {
		persistence: [authMod.indexedDBLocalPersistence, authMod.browserLocalPersistence],
		popupRedirectResolver: authMod.browserPopupRedirectResolver
	});
	auth.languageCode = 'it';
	const db = fsMod.getFirestore(app);
	if (useEmulators()) {
		authMod.connectAuthEmulator(auth, 'http://127.0.0.1:9099', { disableWarnings: true });
		fsMod.connectFirestoreEmulator(db, '127.0.0.1', 8080);
	}
	return { app, auth, db, a: authMod, fs: fsMod };
}

export type Firebase = Awaited<ReturnType<typeof init>>;

export function firebase(): Promise<Firebase> {
	ready ??= init();
	return ready;
}

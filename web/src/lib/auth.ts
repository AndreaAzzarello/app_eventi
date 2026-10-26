// Login con Google o con link via email (Firebase email-link), riautenticazione ed eliminazione dell'account.
import type { Firebase } from './firebase/client';
import { session } from './session.svelte';
import { KEYS, readJson, writeJson } from './storage';

const MESSAGES: Record<string, string> = {
	'auth/invalid-email': 'Indirizzo email non valido.',
	'auth/missing-email': 'Inserisci la tua email.',
	'auth/popup-closed-by-user': 'Hai chiuso la finestra di Google prima di completare l’accesso.',
	'auth/cancelled-popup-request': 'Accesso annullato.',
	'auth/popup-blocked': 'Il browser ha bloccato la finestra di Google: consenti i popup per questo sito o usa il link via email.',
	'auth/network-request-failed': 'Connessione assente o instabile. Riprova.',
	'auth/invalid-action-code': 'Il link non è più valido (forse è già stato usato o è scaduto). Richiedine uno nuovo.',
	'auth/expired-action-code': 'Il link è scaduto. Richiedine uno nuovo.',
	'auth/too-many-requests': 'Troppi tentativi. Aspetta qualche minuto e riprova.',
	'auth/user-mismatch': 'Il link appartiene a un altro account.',
	'auth/requires-recent-login': 'Per sicurezza devi accedere di nuovo prima di continuare.',
	'auth/unauthorized-continue-uri': 'Dominio non autorizzato in Firebase: avvisa il gestore del sito.',
	'auth/unauthorized-domain': 'Dominio non autorizzato in Firebase: avvisa il gestore del sito.'
};

export function authMessage(e: unknown): string {
	const code = (e as { code?: string })?.code ?? '';
	return MESSAGES[code] ?? 'Qualcosa è andato storto. Riprova tra poco.';
}

/** Solo percorsi interni: evita redirect verso altri siti tramite ?next=. */
export const safeNext = (next: string | null) => (next && /^\/(?!\/)/.test(next) ? next : '/');

export async function signInWithGoogle() {
	const fb = await session.start();
	await fb.a.signInWithPopup(fb.auth, new fb.a.GoogleAuthProvider());
}

export async function sendEmailLink(email: string, continuePath: string) {
	const fb = await session.start();
	await fb.a.sendSignInLinkToEmail(fb.auth, email.trim(), {
		url: new URL(continuePath, location.origin).href,
		handleCodeInApp: true
	});
	writeJson(KEYS.emailForSignIn, email.trim());
}

export const savedEmail = () => readJson<string>(KEYS.emailForSignIn, '');

export async function isEmailLink(href: string) {
	const fb = await session.start();
	return fb.a.isSignInWithEmailLink(fb.auth, href);
}

/** Completa l'accesso dal link ricevuto; se l'utente è già dentro, vale come riautenticazione. */
export async function completeEmailLink(email: string, href: string) {
	const fb = await session.start();
	const user = fb.auth.currentUser;
	if (user) {
		await fb.a.reauthenticateWithCredential(user, fb.a.EmailAuthProvider.credentialWithLink(email, href));
	} else {
		await fb.a.signInWithEmailLink(fb.auth, email, href);
	}
	writeJson(KEYS.emailForSignIn, null);
}

/** Firebase chiede un accesso recente (5 minuti) per eliminare l'account. */
export function needsRecentLogin(lastSignIn: number) {
	return Date.now() - lastSignIn > 4 * 60_000;
}

export async function reauthWithGoogle() {
	const fb = await session.start();
	await fb.a.reauthenticateWithPopup(fb.auth.currentUser!, new fb.a.GoogleAuthProvider());
}

/**
 * Elimina tutto: preferiti, proposte (le pending liberando il contatore, come chiedono le regole),
 * profilo e infine l'account di accesso.
 */
export async function deleteAccountAndData() {
	const fb: Firebase = await session.start();
	const { fs, db, auth } = fb;
	const user = auth.currentUser;
	if (!user) throw new Error('not-signed-in');
	const uid = user.uid;

	const favs = await fs.getDocs(fs.collection(db, 'users', uid, 'favorites'));
	for (let i = 0; i < favs.docs.length; i += 450) {
		const b = fs.writeBatch(db);
		for (const d of favs.docs.slice(i, i + 450)) b.delete(d.ref);
		await b.commit();
	}

	const subs = await fs.getDocs(fs.query(fs.collection(db, 'submissions'), fs.where('ownerId', '==', uid)));
	const userRef = fs.doc(db, 'users', uid);
	for (const s of subs.docs) {
		const b = fs.writeBatch(db);
		b.delete(s.ref);
		if (s.data().status === 'pending') b.update(userRef, { pendingCount: fs.increment(-1), lastSubmissionId: s.id });
		await b.commit();
	}

	await fs.deleteDoc(userRef);
	await fb.a.deleteUser(user);
	for (const k of [KEYS.favorites, KEYS.session, KEYS.loginHintShown, KEYS.emailForSignIn]) writeJson(k, null);
}

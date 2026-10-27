// Operazioni dell'admin. Le regole Firestore le ricontrollano tutte (email admin verificata).
import { fromData, type Event, type EventInput } from './event';
import { session } from './session.svelte';
import { fromSnap, type Submission } from './submissions';

const PAGE = 100;

/** Eventi finiti da meno di 30 giorni o futuri, a pagine: mai l'intera collezione. */
export async function listEvents(after?: Event): Promise<Event[]> {
	const { fs, db } = await session.start();
	const cutoff = Date.now() - 30 * 24 * 3600_000;
	const base = fs.query(fs.collection(db, 'events'), fs.where('endTime', '>=', cutoff), fs.orderBy('endTime'));
	const snap = await fs.getDocs(
		after ? fs.query(base, fs.startAfter(after.endTime), fs.limit(PAGE)) : fs.query(base, fs.limit(PAGE))
	);
	return snap.docs.map((d) => fromData(d.id, d.data()));
}
export const PAGE_SIZE = PAGE;

export async function loadEvent(id: string): Promise<Event | null> {
	const { fs, db } = await session.start();
	const snap = await fs.getDoc(fs.doc(db, 'events', id));
	return snap.exists() ? fromData(snap.id, snap.data()) : null;
}

/** Crea o sostituisce un evento. Un evento importato toccato a mano diventa "manual" (l'importer non lo sovrascrive più). */
export async function saveEvent(id: string | null, input: EventInput): Promise<string> {
	const { fs, db } = await session.start();
	const ref = id ? fs.doc(db, 'events', id) : fs.doc(fs.collection(db, 'events'));
	const old = id ? (await fs.getDoc(ref)).data() : undefined;
	const now = Date.now();
	const source = !old || old.source === 'scraper' ? 'manual' : old.source;
	await fs.setDoc(ref, {
		...input,
		source,
		sourceUrl: (old?.sourceUrl as string) ?? '',
		createdAt: (old?.createdAt as number) ?? now,
		updatedAt: now,
		// La frazione vale solo se l'admin non ha spostato il luogo in un altro comune.
		...(old?.locality && input.city === old.city ? { locality: old.locality } : {}),
		...(old?.submittedBy ? { submittedBy: old.submittedBy } : {})
	});
	return ref.id;
}

export async function deleteEvent(id: string) {
	const { fs, db } = await session.start();
	await fs.deleteDoc(fs.doc(db, 'events', id));
}

export async function pendingSubmissions(): Promise<Submission[]> {
	const { fs, db } = await session.start();
	const snap = await fs.getDocs(
		fs.query(fs.collection(db, 'submissions'), fs.where('status', '==', 'pending'), fs.orderBy('createdAt'), fs.limit(100))
	);
	return snap.docs.map((d) => fromSnap(d.id, d.data()));
}

const EVENT_KEYS = [
	'title', 'shortDescription', 'category', 'priceType', 'startTime', 'endTime', 'venueName', 'address',
	'lat', 'lng', 'imageUrl', 'ticketUrl', 'tags', 'geohash', 'city', 'citySlug', 'province', 'region'
] as const;

/** Approva: copia in events (source "user", submittedBy interno), chiude la proposta, libera il posto dell'autore. */
export async function approve(s: Submission): Promise<string> {
	const { fs, db } = await session.start();
	const eventRef = fs.doc(fs.collection(db, 'events'));
	const now = Date.now();
	const data = Object.fromEntries(EVENT_KEYS.map((k) => [k, s[k]]));
	const b = fs.writeBatch(db);
	b.set(eventRef, { ...data, source: 'user', sourceUrl: '', submittedBy: s.ownerId, createdAt: now, updatedAt: now });
	b.update(fs.doc(db, 'submissions', s.id), { status: 'approved', eventId: eventRef.id, reviewedAt: fs.serverTimestamp() });
	b.update(fs.doc(db, 'users', s.ownerId), { pendingCount: fs.increment(-1) });
	await b.commit();
	return eventRef.id;
}

export async function reject(s: Submission, reason: string) {
	const { fs, db } = await session.start();
	const b = fs.writeBatch(db);
	b.update(fs.doc(db, 'submissions', s.id), {
		status: 'rejected',
		rejectReason: reason.trim().slice(0, 500),
		reviewedAt: fs.serverTimestamp()
	});
	b.update(fs.doc(db, 'users', s.ownerId), { pendingCount: fs.increment(-1) });
	await b.commit();
}

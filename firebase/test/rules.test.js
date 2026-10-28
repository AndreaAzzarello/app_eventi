import { readFileSync } from 'node:fs';
import { afterAll, beforeAll, beforeEach, describe, it } from 'vitest';
import { assertFails, assertSucceeds, initializeTestEnvironment } from '@firebase/rules-unit-testing';
import {
  collection, deleteDoc, doc, getDoc, getDocs, increment, query, serverTimestamp, setDoc,
  updateDoc, where, writeBatch,
} from 'firebase/firestore';

let env;
const ADMIN = { email: 'azzatubo@gmail.com', email_verified: true };

const event = (over = {}) => ({
  title: 'Concerto in piazza', shortDescription: 'Musica dal vivo', category: 'music', priceType: 'free',
  startTime: 1_800_000_000_000, endTime: 1_800_003_600_000, venueName: 'Piazza Grande',
  address: 'Piazza Grande, 41121 Modena', lat: 44.6458, lng: 10.9256, imageUrl: '',
  ticketUrl: 'https://example.org/biglietti', tags: ['live'], geohash: 'srbj4w1t0q',
  city: 'Modena', citySlug: 'modena', province: 'MO', region: 'Emilia-Romagna', ...over,
});

const db = (uid, token) => (uid ? env.authenticatedContext(uid, token) : env.unauthenticatedContext()).firestore();
const seed = (fn) => env.withSecurityRulesDisabled((ctx) => fn(ctx.firestore()));

// Proposta creata come fa il client: proposta + contatore nello stesso batch.
function submit(fs, uid, sid, data = {}, counterDelta = 1) {
  const b = writeBatch(fs);
  b.set(doc(fs, 'submissions', sid), {
    ...event(), ownerId: uid, status: 'pending', createdAt: serverTimestamp(), ...data,
  });
  if (counterDelta !== null) {
    b.update(doc(fs, 'users', uid), { pendingCount: increment(counterDelta), lastSubmissionId: sid });
  }
  return b.commit();
}

beforeAll(async () => {
  env = await initializeTestEnvironment({
    projectId: 'demo-eventi',
    firestore: { rules: readFileSync(new URL('../firestore.rules', import.meta.url), 'utf8') },
  });
});
afterAll(() => env.cleanup());
beforeEach(async () => {
  await env.clearFirestore();
  await seed(async (fs) => {
    await setDoc(doc(fs, 'events', 'e1'), { ...event(), source: 'scraper' });
    await setDoc(doc(fs, 'users', 'alice'), { name: 'Alice', city: '', createdAt: new Date(), pendingCount: 0 });
  });
});

describe('events', () => {
  it('lettura pubblica', () => assertSucceeds(getDoc(doc(db(), 'events', 'e1'))));
  it('anonimo e utente non scrivono', async () => {
    await assertFails(setDoc(doc(db(), 'events', 'x'), { ...event(), source: 'manual' }));
    await assertFails(setDoc(doc(db('alice'), 'events', 'x'), { ...event(), source: 'manual' }));
    await assertFails(deleteDoc(doc(db('alice'), 'events', 'e1')));
  });
  it('admin con email non verificata non scrive', () =>
    assertFails(setDoc(doc(db('adm', { email: ADMIN.email, email_verified: false }), 'events', 'x'),
      { ...event(), source: 'manual' })));
  it('admin crea, modifica ed elimina', async () => {
    const fs = db('adm', ADMIN);
    await assertSucceeds(setDoc(doc(fs, 'events', 'x'), { ...event(), source: 'manual', createdAt: 1, updatedAt: 1 }));
    await assertSucceeds(updateDoc(doc(fs, 'events', 'x'), { title: 'Nuovo titolo' }));
    await assertSucceeds(deleteDoc(doc(fs, 'events', 'x')));
  });
  it('approxLocation: booleano ammesso, altri tipi no', async () => {
    const fs = db('adm', ADMIN);
    await assertSucceeds(updateDoc(doc(fs, 'events', 'e1'), { approxLocation: true }));
    await assertFails(updateDoc(doc(fs, 'events', 'e1'), { approxLocation: 'si' }));
  });
  it('locality: ammessa fino a 80 caratteri', async () => {
    const fs = db('adm', ADMIN);
    await assertSucceeds(setDoc(doc(fs, 'events', 'x'), { ...event(), source: 'manual', locality: "Sant'Agostino" }));
    await assertSucceeds(updateDoc(doc(fs, 'events', 'e1'), { locality: 'a'.repeat(80) }));
    await assertFails(updateDoc(doc(fs, 'events', 'e1'), { locality: 'a'.repeat(81) }));
    await assertFails(updateDoc(doc(fs, 'events', 'e1'), { locality: 5 }));
  });
  it('longRunning: booleano ammesso, altri tipi no', async () => {
    const fs = db('adm', ADMIN);
    await assertSucceeds(updateDoc(doc(fs, 'events', 'e1'), { longRunning: true }));
    await assertFails(updateDoc(doc(fs, 'events', 'e1'), { longRunning: 'si' }));
  });
  it("campi di servizio dell'importer: tipi controllati", async () => {
    const fs = db('adm', ADMIN);
    await assertSucceeds(updateDoc(doc(fs, 'events', 'e1'), { contentHash: 'abc', importRegion: 'lombardia', missingRuns: 1, removedAt: 5 }));
    await assertFails(updateDoc(doc(fs, 'events', 'e1'), { contentHash: 5 }));
    await assertFails(updateDoc(doc(fs, 'events', 'e1'), { missingRuns: 'x' }));
    await assertFails(updateDoc(doc(fs, 'events', 'e1'), { importRegion: 'a'.repeat(41) }));
  });
  it.each([
    ['link javascript:', { ticketUrl: 'javascript:alert(1)' }],
    ["fine prima dell'inizio", { endTime: 1 }],
    ['categoria sconosciuta', { category: 'party' }],
    ['coordinate 0,0', { lat: 0, lng: 0 }],
    ['titolo vuoto', { title: '' }],
    ['titolo troppo lungo', { title: 'x'.repeat(201) }],
    ['startTime stringa', { startTime: '2026-01-01' }],
    ['campo sconosciuto', { hacked: true }],
    ['senza geohash', { geohash: undefined }],
    ['source non valida', { source: 'bot' }],
  ])('admin: rifiuta %s', (_, over) => {
    const data = { ...event(), source: 'manual', ...over };
    for (const k of Object.keys(data)) if (data[k] === undefined) delete data[k];
    return assertFails(setDoc(doc(db('adm', ADMIN), 'events', 'x'), data));
  });
});

describe('coverage', () => {
  it('lettura pubblica, scrittura mai (nemmeno dall\'admin: scrive l\'importer)', async () => {
    await seed((fs) => setDoc(doc(fs, 'coverage', 'lombardia'), { name: 'Lombardia', updatedAt: 1, comuni: [] }));
    await assertSucceeds(getDoc(doc(db(), 'coverage', 'lombardia')));
    await assertSucceeds(getDocs(collection(db(), 'coverage')));
    await assertFails(setDoc(doc(db('alice'), 'coverage', 'x'), { name: 'X' }));
    await assertFails(setDoc(doc(db('adm', ADMIN), 'coverage', 'x'), { name: 'X' }));
    await assertFails(updateDoc(doc(db('adm', ADMIN), 'coverage', 'lombardia'), { name: 'Y' }));
    await assertFails(deleteDoc(doc(db('adm', ADMIN), 'coverage', 'lombardia')));
  });
});

describe('stats', () => {
  it('lettura pubblica, scrittura mai (nemmeno admin: scrive solo importer)', async () => {
    await seed((fs) => setDoc(doc(fs, 'stats', 'lombardia_2026-11'), { region: 'lombardia', month: '2026-11', events: 412 }));
    await assertSucceeds(getDoc(doc(db(), 'stats', 'lombardia_2026-11')));
    await assertSucceeds(getDocs(collection(db(), 'stats')));
    await assertFails(setDoc(doc(db('alice'), 'stats', 'x_2026-11'), { events: 1 }));
    await assertFails(setDoc(doc(db('adm', ADMIN), 'stats', 'x_2026-11'), { events: 1 }));
    await assertFails(updateDoc(doc(db('adm', ADMIN), 'stats', 'lombardia_2026-11'), { events: 2 }));
    await assertFails(deleteDoc(doc(db('adm', ADMIN), 'stats', 'lombardia_2026-11')));
  });
});

describe('users: homePlace', () => {
  const ref = (uid = 'alice') => doc(db(uid), 'users', uid);
  const place = { label: 'Lecco', lat: 45.85, lng: 9.39, slug: 'lecco', region: 'Lombardia' };
  it('il proprietario salva e cambia la zona', async () => {
    await assertSucceeds(updateDoc(ref(), { homePlace: place }));
    await assertSucceeds(updateDoc(ref(), { homePlace: { label: 'Vicino a Lecco', lat: 45.8, lng: 9.4 } }));
  });
  it('alla creazione del profilo', () =>
    assertSucceeds(setDoc(doc(db('bob'), 'users', 'bob'), { name: 'Bob', createdAt: serverTimestamp(), pendingCount: 0, homePlace: place })));
  it.each([
    ['campo extra', { ...place, extra: 1 }],
    ['senza etichetta', { lat: 1, lng: 1 }],
    ['etichetta vuota', { ...place, label: '' }],
    ['etichetta lunga', { ...place, label: 'a'.repeat(81) }],
    ['latitudine fuori scala', { ...place, lat: 91 }],
    ['coordinate come stringhe', { ...place, lat: '45', lng: '9' }],
    ['non è una mappa', 'Lecco'],
  ])('rifiuta: %s', (_, homePlace) => assertFails(updateDoc(ref(), { homePlace })));
  it("l'estraneo non la scrive", () => assertFails(updateDoc(doc(db('bob'), 'users', 'alice'), { homePlace: place })));
});

describe('users', () => {
  it('solo il proprietario legge', async () => {
    await assertSucceeds(getDoc(doc(db('alice'), 'users', 'alice')));
    await assertFails(getDoc(doc(db('bob'), 'users', 'alice')));
    await assertFails(getDoc(doc(db(), 'users', 'alice')));
  });
  it('profilo nuovo con contatore a zero', () =>
    assertSucceeds(setDoc(doc(db('bob'), 'users', 'bob'), { name: 'Bob', createdAt: serverTimestamp(), pendingCount: 0 })));
  it('rifiuta profilo con contatore barato, di un altro utente o con campi extra', async () => {
    await assertFails(setDoc(doc(db('bob'), 'users', 'bob'), { createdAt: serverTimestamp(), pendingCount: -3 }));
    await assertFails(setDoc(doc(db('bob'), 'users', 'carl'), { createdAt: serverTimestamp(), pendingCount: 0 }));
    await assertFails(setDoc(doc(db('bob'), 'users', 'bob'), { createdAt: serverTimestamp(), pendingCount: 0, role: 'admin' }));
  });
  it('aggiorna nome e città ma non il contatore a mano', async () => {
    await assertSucceeds(updateDoc(doc(db('alice'), 'users', 'alice'), { name: 'Ali', city: 'Modena' }));
    await assertFails(updateDoc(doc(db('alice'), 'users', 'alice'), { pendingCount: -1 }));
    await assertFails(updateDoc(doc(db('alice'), 'users', 'alice'), { createdAt: new Date(0) }));
    await assertFails(updateDoc(doc(db('bob'), 'users', 'alice'), { name: 'Bob' }));
  });
  it('preferiti solo del proprietario', async () => {
    await assertSucceeds(setDoc(doc(db('alice'), 'users/alice/favorites/e1'), { addedAt: 1 }));
    await assertSucceeds(getDocs(collection(db('alice'), 'users/alice/favorites')));
    await assertFails(getDocs(collection(db('bob'), 'users/alice/favorites')));
    await assertFails(setDoc(doc(db('bob'), 'users/alice/favorites/e1'), { addedAt: 1 }));
    await assertFails(setDoc(doc(db('alice'), 'users/alice/favorites/e2'), { addedAt: 1, note: 'x' }));
    await assertSucceeds(deleteDoc(doc(db('alice'), 'users/alice/favorites/e1')));
  });
  it('profilo non eliminabile con proposte pending', async () => {
    await submit(db('alice'), 'alice', 's1');
    await assertFails(deleteDoc(doc(db('alice'), 'users', 'alice')));
  });
  it('profilo eliminabile senza pending', () => assertSucceeds(deleteDoc(doc(db('alice'), 'users', 'alice'))));
  it("l'admin non legge i profili", () => assertFails(getDoc(doc(db('adm', ADMIN), 'users', 'alice'))));
});

describe('submissions', () => {
  it('crea una proposta col contatore', () => assertSucceeds(submit(db('alice'), 'alice', 's1')));
  it('anonimo non propone', () =>
    assertFails(setDoc(doc(db(), 'submissions', 's1'), { ...event(), ownerId: 'x', status: 'pending', createdAt: serverTimestamp() })));
  it('rifiuta senza incremento del contatore', () => assertFails(submit(db('alice'), 'alice', 's1', {}, null)));
  it('rifiuta incremento di 2', () => assertFails(submit(db('alice'), 'alice', 's1', {}, 2)));
  it('rifiuta status diverso da pending', () => assertFails(submit(db('alice'), 'alice', 's1', { status: 'approved' })));
  it('rifiuta ownerId di un altro', () => assertFails(submit(db('alice'), 'alice', 's1', { ownerId: 'bob' })));
  it('rifiuta dati non validi', () => assertFails(submit(db('alice'), 'alice', 's1', { imageUrl: 'data:image/png;base64,AAA' })));
  it('rifiuta locality (solo importer/admin)', () => assertFails(submit(db('alice'), 'alice', 's1', { locality: 'Frazione' })));
  it('rifiuta longRunning (solo importer/admin)', () => assertFails(submit(db('alice'), 'alice', 's1', { longRunning: true })));
  it('rifiuta campi interni (submittedBy)', () => assertFails(submit(db('alice'), 'alice', 's1', { submittedBy: 'alice' })));
  it('massimo 5 pending', async () => {
    const fs = db('alice');
    for (let i = 1; i <= 5; i++) await assertSucceeds(submit(fs, 'alice', `s${i}`));
    await assertFails(submit(fs, 'alice', 's6'));
  });
  it('il contatore non sale senza una proposta vera', () =>
    assertFails(updateDoc(doc(db('alice'), 'users', 'alice'), { pendingCount: 1, lastSubmissionId: 'fantasma' })));

  describe('con una proposta pending', () => {
    beforeEach(() => submit(db('alice'), 'alice', 's1'));

    it("legge il proprietario e l'admin, non gli altri", async () => {
      await assertSucceeds(getDoc(doc(db('alice'), 'submissions', 's1')));
      await assertSucceeds(getDocs(query(collection(db('alice'), 'submissions'), where('ownerId', '==', 'alice'))));
      await assertSucceeds(getDoc(doc(db('adm', ADMIN), 'submissions', 's1')));
      await assertFails(getDoc(doc(db('bob'), 'submissions', 's1')));
      await assertFails(getDoc(doc(db(), 'submissions', 's1')));
      await assertFails(getDocs(collection(db('bob'), 'submissions')));
    });
    it('il proprietario non cambia lo status né i dati', async () => {
      await assertFails(updateDoc(doc(db('alice'), 'submissions', 's1'), { status: 'approved' }));
      await assertFails(updateDoc(doc(db('alice'), 'submissions', 's1'), { title: 'Altro' }));
    });
    it('admin approva: evento + stato + contatore', async () => {
      const fs = db('adm', ADMIN);
      const b = writeBatch(fs);
      b.set(doc(fs, 'events', 'new1'), { ...event(), source: 'user', submittedBy: 'alice', sourceUrl: '', createdAt: 1, updatedAt: 1 });
      b.update(doc(fs, 'submissions', 's1'), { status: 'approved', eventId: 'new1', reviewedAt: serverTimestamp() });
      b.update(doc(fs, 'users', 'alice'), { pendingCount: increment(-1) });
      await assertSucceeds(b.commit());
    });
    it("admin: approvare senza creare l'evento è vietato", async () => {
      const fs = db('adm', ADMIN);
      const b = writeBatch(fs);
      b.update(doc(fs, 'submissions', 's1'), { status: 'approved', eventId: 'manca', reviewedAt: serverTimestamp() });
      b.update(doc(fs, 'users', 'alice'), { pendingCount: increment(-1) });
      await assertFails(b.commit());
    });
    it('admin: rifiuto senza motivo vietato, con motivo ok', async () => {
      const fs = db('adm', ADMIN);
      const reject = (reason) => {
        const b = writeBatch(fs);
        b.update(doc(fs, 'submissions', 's1'), { status: 'rejected', rejectReason: reason, reviewedAt: serverTimestamp() });
        b.update(doc(fs, 'users', 'alice'), { pendingCount: increment(-1) });
        return b.commit();
      };
      await assertFails(reject(''));
      await assertSucceeds(reject('Evento duplicato'));
    });
    it('admin: cambiare stato senza scalare il contatore è vietato', () =>
      assertFails(updateDoc(doc(db('adm', ADMIN), 'submissions', 's1'),
        { status: 'rejected', rejectReason: 'Spam spam', reviewedAt: serverTimestamp() })));
    it('admin non cancella una pending', () => assertFails(deleteDoc(doc(db('adm', ADMIN), 'submissions', 's1'))));
    it('il proprietario ritira la proposta liberando il posto', async () => {
      const fs = db('alice');
      const b = writeBatch(fs);
      b.delete(doc(fs, 'submissions', 's1'));
      b.update(doc(fs, 'users', 'alice'), { pendingCount: increment(-1), lastSubmissionId: 's1' });
      await assertSucceeds(b.commit());
      await assertSucceeds(deleteDoc(doc(fs, 'users', 'alice')));
    });
    it('ritirare senza scalare il contatore è vietato', () => assertFails(deleteDoc(doc(db('alice'), 'submissions', 's1'))));
    it('scalare il contatore senza ritirare è vietato', () =>
      assertFails(updateDoc(doc(db('alice'), 'users', 'alice'), { pendingCount: increment(-1), lastSubmissionId: 's1' })));
    it('un altro utente non la cancella', () => assertFails(deleteDoc(doc(db('bob'), 'submissions', 's1'))));
  });
});

describe('resto del database', () => {
  it('chiuso', async () => {
    await assertFails(getDoc(doc(db('adm', ADMIN), 'config', 'x')));
    await assertFails(setDoc(doc(db('alice'), 'config', 'x'), { a: 1 }));
  });
});

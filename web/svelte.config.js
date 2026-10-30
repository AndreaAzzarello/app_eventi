import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import adapter from '@sveltejs/adapter-cloudflare';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

// Gli script inline di app.html (tema, luogo salvato) non possono avere il nonce: /offline è prerenderizzata.
// Si autorizzano per hash, calcolato qui sul testo come lo vede il browser (a capo normalizzati: stesso hash su Windows e Linux).
const inlineScripts = [...readFileSync(new URL('./src/app.html', import.meta.url), 'utf8').matchAll(/<script>([\s\S]*?)<\/script>/g)].map(
	(m) => `sha256-${createHash('sha256').update(m[1].replace(/\r\n/g, '\n')).digest('base64')}`
);

/** @type {import('@sveltejs/kit').Config} */
export default {
	preprocess: vitePreprocess(),
	kit: {
		adapter: adapter(),
		serviceWorker: { register: false },
		// auto: nonce sulle pagine dinamiche, hash su quelle prerenderizzate. frame-ancestors resta fuori dai <meta>: c'è anche X-Frame-Options.
		csp: {
			mode: 'auto',
			directives: {
				'default-src': ['self'],
				// apis.google.com: il popup di accesso con Google (Firebase Auth) carica da lì il suo script.
				'script-src': ['self', 'https://apis.google.com', ...inlineScripts],
				// unsafe-inline: stili inline di Svelte (transizioni, style=) e di Leaflet.
				'style-src': ['self', 'unsafe-inline'],
				// Immagini degli eventi: da siti di Comuni, Open Data Hub, Ticketmaster e URL proposti (https), più tile OSM.
				'img-src': ['self', 'data:', 'blob:', 'https:'],
				'font-src': ['self'],
				// googleapis.com: Firestore, Identity Toolkit, Secure Token. Le due porte locali sono gli emulatori (e2e e sviluppo).
				'connect-src': ['self', 'https://*.googleapis.com', 'http://127.0.0.1:9099', 'http://127.0.0.1:8080'],
				'frame-src': ['https://*.firebaseapp.com', 'https://accounts.google.com', 'http://127.0.0.1:9099'],
				'worker-src': ['self'],
				'manifest-src': ['self'],
				'object-src': ['none'],
				'base-uri': ['self'],
				'form-action': ['self'],
				'frame-ancestors': ['none']
			}
		}
	}
};

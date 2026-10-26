/// <reference types="@sveltejs/kit" />
/// <reference no-default-lib="true"/>
/// <reference lib="esnext" />
/// <reference lib="webworker" />
// App shell in cache: JS/CSS/font/icone della build, pagina offline. Le pagine HTML vanno in rete
// prima (dati freschi) e cadono sulla copia in cache o su /offline. API, Firebase e tile: mai in cache qui.
import { build, files, prerendered, version } from '$service-worker';

const sw = self as unknown as ServiceWorkerGlobalScope;
const SHELL = `shell-${version}`;
const PAGES = 'pages-v1';
const ASSETS = [...build, ...files.filter((f) => !f.endsWith('og.png')), ...prerendered];

sw.addEventListener('install', (event) => {
	event.waitUntil(
		caches
			.open(SHELL)
			.then((c) => c.addAll(ASSETS))
			.then(() => sw.skipWaiting())
	);
});

sw.addEventListener('activate', (event) => {
	event.waitUntil(
		caches
			.keys()
			.then((keys) => Promise.all(keys.filter((k) => k !== SHELL && k !== PAGES).map((k) => caches.delete(k))))
			.then(() => sw.clients.claim())
	);
});

sw.addEventListener('fetch', (event) => {
	const req = event.request;
	if (req.method !== 'GET') return;
	const url = new URL(req.url);
	if (url.origin !== sw.location.origin || url.pathname.startsWith('/api/')) return;

	if (ASSETS.includes(url.pathname)) {
		event.respondWith(caches.match(req).then((hit) => hit ?? fetch(req)));
		return;
	}
	if (req.mode === 'navigate') {
		event.respondWith(
			fetch(req)
				.then((res) => {
					// Solo pagine pubbliche e riuscite: niente account, admin o login in cache.
					if (res.ok && !/^\/(admin|account|accedi|proponi)/.test(url.pathname)) {
						const copy = res.clone();
						caches.open(PAGES).then(async (c) => {
							await c.put(req, copy);
							const keys = await c.keys();
							if (keys.length > 40) await c.delete(keys[0]); // tetto: le pagine più vecchie escono
						});
					}
					return res;
				})
				.catch(async () => (await caches.match(req)) ?? (await caches.match('/offline'))!)
		);
	}
});

import type { Handle } from '@sveltejs/kit';

// Intestazioni di sicurezza delle risposte del Worker (pagine e /api). Gli asset statici le prendono da static/_headers:
// Cloudflare Pages non applica _headers alle risposte del Worker. Tenere le due liste allineate.
// same-origin-allow-popups: il popup di accesso con Google deve poter parlare con la pagina che lo apre.
const SECURITY_HEADERS = {
	'x-content-type-options': 'nosniff',
	'referrer-policy': 'strict-origin-when-cross-origin',
	'permissions-policy': 'camera=(), microphone=(), geolocation=(self), payment=()',
	'x-frame-options': 'DENY',
	'cross-origin-opener-policy': 'same-origin-allow-popups'
};

export const handle: Handle = async ({ event, resolve }) => {
	const response = await resolve(event);
	for (const [name, value] of Object.entries(SECURITY_HEADERS)) response.headers.set(name, value);
	return response;
};

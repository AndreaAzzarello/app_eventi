import { describe, expect, it } from 'vitest';
import { safeNext } from './auth';

const O = 'https://eventi-vicini.pages.dev';
const next = (v: string | null) => safeNext(v, O);

describe('safeNext', () => {
	it('percorsi interni passano, con query e hash', () => {
		expect(next('/account')).toBe('/account');
		expect(next('/eventi/x-1?a=1#b')).toBe('/eventi/x-1?a=1#b');
		expect(next('/%09/evil.com')).toBe('/%09/evil.com'); // %09 non è un tab: resta un percorso del sito
	});
	it('vuoto o assente: home', () => {
		expect(next(null)).toBe('/');
		expect(next('')).toBe('/');
	});
	it.each(['//evil.com', 'https://evil.com', '/\t/evil.com', '/\\evil.com', '\\\\evil.com', 'javascript:alert(1)', 'http://eventi-vicini.pages.dev'])(
		'%j non esce dal sito',
		(v) => expect(next(v)).toBe('/')
	);
});

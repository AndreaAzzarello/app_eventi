import { describe, expect, it } from 'vitest';
import { imageSources } from './images';

describe('imageSources', () => {
	it('URL Plone con scala: srcset con le scale standard', () => {
		const r = imageSources('https://x.it/ev/foo/@@images/image/large');
		expect(r.src).toBe('https://x.it/ev/foo/@@images/image/large');
		expect(r.srcset).toBe(
			'https://x.it/ev/foo/@@images/image/preview 400w, https://x.it/ev/foo/@@images/image/large 800w, ' +
				'https://x.it/ev/foo/@@images/image/larger 1000w, https://x.it/ev/foo/@@images/image/great 1200w'
		);
	});
	it('mantiene la query string', () => {
		expect(imageSources('https://x.it/a/@@images/image/preview?v=1').srcset).toContain('/large?v=1 800w');
	});
	it.each([
		'https://www.comune.modena.it/ev/@@images/image-800-e4aa95d60d3a61a549ea6646641b5e70.jpeg',
		'https://x.it/foto.jpg',
		'https://x.it/@@images/image/original'
	])('altri URL: solo src (%s)', (u) => expect(imageSources(u)).toEqual({ src: u }));
});

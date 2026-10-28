<script lang="ts">
	import { onMount } from 'svelte';
	import AudioLines from '@lucide/svelte/icons/audio-lines';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import Baby from '@lucide/svelte/icons/baby';
	import Calendar from '@lucide/svelte/icons/calendar';
	import Check from '@lucide/svelte/icons/check';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Heart from '@lucide/svelte/icons/heart';
	import Landmark from '@lucide/svelte/icons/landmark';
	import List from '@lucide/svelte/icons/list';
	import LocateFixed from '@lucide/svelte/icons/locate-fixed';
	import Mail from '@lucide/svelte/icons/mail';
	import Map from '@lucide/svelte/icons/map';
	import MapPin from '@lucide/svelte/icons/map-pin';
	import Moon from '@lucide/svelte/icons/moon';
	import Pencil from '@lucide/svelte/icons/pencil';
	import Plus from '@lucide/svelte/icons/plus';
	import Search from '@lucide/svelte/icons/search';
	import Share2 from '@lucide/svelte/icons/share-2';
	import ShoppingBasket from '@lucide/svelte/icons/shopping-basket';
	import SlidersHorizontal from '@lucide/svelte/icons/sliders-horizontal';
	import Sun from '@lucide/svelte/icons/sun';
	import Tag from '@lucide/svelte/icons/tag';
	import Ticket from '@lucide/svelte/icons/ticket';
	import Trash from '@lucide/svelte/icons/trash';
	import Trophy from '@lucide/svelte/icons/trophy';
	import User from '@lucide/svelte/icons/user';
	import Utensils from '@lucide/svelte/icons/utensils';
	import X from '@lucide/svelte/icons/x';
	import ErrorMessage from '$lib/components/ErrorMessage.svelte';
	import { CATEGORIES } from '$lib/event';
	import { fmtNum, monthKeys, monthLine } from '$lib/format';

	const space = [1, 2, 3, 4, 5, 6, 7];
	const grays = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900];
	const roles = ['bg', 'surface', 'surface-2', 'border', 'border-strong', 'text', 'muted', 'accent', 'accent-hover', 'danger'];
	const sizes = ['xs', 'sm', 'md', 'lg', 'xl', '2xl', '3xl'];
	const icons = { MapPin, Calendar, Heart, Share2, Map, List, Ticket, Search, User, Plus, Sun, Moon, X, Check, LocateFixed, ArrowLeft, Mail, SlidersHorizontal, Trash, Pencil, ExternalLink };
	const categoryIcons = { music: AudioLines, food: Utensils, sport: Trophy, culture: Landmark, kids: Baby, market: ShoppingBasket, other: Tag };
	const keys = monthKeys();

	// Colori risolti dal browser (light-dark() compreso) e contrasto sullo sfondo.
	let resolved: Record<string, { rgb: string; onBg: string; onSurface: string }> = $state({});
	let probe: HTMLSpanElement;

	const lum = (rgb: string) => {
		const [r, g, b] = (rgb.match(/[\d.]+/g) ?? []).slice(0, 3).map((v) => {
			const c = Number(v) / 255;
			return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
		});
		return 0.2126 * r + 0.7152 * g + 0.0722 * b;
	};
	const ratio = (a: string, b: string) => {
		const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p);
		return ((x + 0.05) / (y + 0.05)).toFixed(1).replace('.', ',');
	};

	function measure() {
		const get = (name: string) => {
			probe.style.backgroundColor = `var(--${name})`;
			return getComputedStyle(probe).backgroundColor;
		};
		const bg = get('bg');
		const surface = get('surface');
		resolved = Object.fromEntries(
			[...roles, ...grays.map((g) => `gray-${g}`)].map((n) => {
				const rgb = get(n);
				return [n, { rgb, onBg: ratio(rgb, bg), onSurface: ratio(rgb, surface) }];
			})
		);
	}

	onMount(() => {
		measure();
		// Il tema può cambiare mentre la pagina è aperta.
		const mo = new MutationObserver(measure);
		mo.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
		const mq = matchMedia('(prefers-color-scheme: dark)');
		mq.addEventListener('change', measure);
		return () => {
			mo.disconnect();
			mq.removeEventListener('change', measure);
		};
	});
</script>

<span bind:this={probe} class="probe" aria-hidden="true"></span>

<h1>Stile</h1>
<p class="muted">Riferimento del design system. I valori stanno in <code>src/lib/styles/tokens.css</code>; <code>design.test.ts</code> fallisce se il codice li aggira.</p>

<section aria-labelledby="s-space">
	<h2 id="s-space">Spaziatura</h2>
	<p class="muted">Multipli di 8, più il 4 per i dettagli. Margini, padding, gap, raggi e controlli usano solo questi token.</p>
	<ul class="plain">
		{#each space as n (n)}
			<li class="space-row">
				<code>--space-{n}</code>
				<span class="bar" style="width: var(--space-{n})"></span>
			</li>
		{/each}
	</ul>
	<p class="muted">Raggi: <code>--radius-sm</code>, <code>--radius</code>, <code>--radius-full</code> (solo avatar e interruttori). Controlli: <code>--control</code>, <code>--control-sm</code>.</p>
</section>

<section aria-labelledby="s-col">
	<h2 id="s-col">Colore</h2>
	<p class="muted">Dieci grigi caldi e un solo accento, il terracotta, per azioni primarie, link, focus e stato attivo. Il rosso d’errore è un cremisi più freddo e compare sempre con icona e testo. Contrasti calcolati nel tema in uso.</p>
	<h3>Ruoli</h3>
	<ul class="plain swatches">
		{#each roles as n (n)}
			<li>
				<span class="chipcolor" style="background: var(--{n})"></span>
				<span><code>--{n}</code> <span class="muted num">{resolved[n]?.rgb ?? ''}</span></span>
				<span class="num muted">{resolved[n] ? `${resolved[n].onBg} su sfondo · ${resolved[n].onSurface} su superficie` : ''}</span>
			</li>
		{/each}
	</ul>
	<h3>Scala dei grigi</h3>
	<ul class="plain grays">
		{#each grays as g (g)}
			<li><span class="chipcolor" style="background: var(--gray-{g})"></span><code>{g}</code></li>
		{/each}
	</ul>
</section>

<section aria-labelledby="s-type">
	<h2 id="s-type">Tipografia</h2>
	<p class="muted">Due pesi, 400 e 600. Titoli in Fraunces, testo con il font di sistema. Mai tutto maiuscolo.</p>
	<ul class="plain">
		{#each sizes as s (s)}
			<li class="type-row"><code>--text-{s}</code><span style="font-size: var(--text-{s})">Concerto in piazza, ott 2026</span></li>
		{/each}
	</ul>
	<p><span style="font-weight: var(--fw-regular)">Peso 400, testo corrente.</span> <span style="font-weight: var(--fw-strong)">Peso 600, etichette e titoli.</span></p>
	<p>Numeri con cifre tabellari: <span class="num">{fmtNum(1234)} · {fmtNum(56)} · {fmtNum(7)}</span></p>
</section>

<section aria-labelledby="s-icon">
	<h2 id="s-icon">Icone</h2>
	<p class="muted">Solo Lucide, a linea, 16/20/24 con tratto 2. Decorative con <code>aria-hidden</code>; le icone senza testo hanno l’etichetta sul bottone.</p>
	<ul class="plain icon-grid">
		{#each Object.entries(icons) as [name, Icon] (name)}
			<li><Icon size={20} aria-hidden="true" /><code>{name}</code></li>
		{/each}
	</ul>
	<h3>Categorie</h3>
	<p class="muted">Si distinguono per icona, non per colore.</p>
	<ul class="plain icon-grid">
		{#each Object.entries(categoryIcons) as [key, Icon] (key)}
			<li><Icon size={20} aria-hidden="true" />{CATEGORIES[key as keyof typeof CATEGORIES]}</li>
		{/each}
	</ul>
	<p class="sizes"><MapPin size={16} aria-hidden="true" /> 16 <MapPin size={20} aria-hidden="true" /> 20 <MapPin size={24} aria-hidden="true" /> 24</p>
</section>

<section aria-labelledby="s-comp">
	<h2 id="s-comp">Componenti</h2>
	<h3>Bottoni</h3>
	<p class="row">
		<button class="btn btn-primary" type="button"><Plus size={20} aria-hidden="true" /> Primario</button>
		<button class="btn" type="button">Secondario</button>
		<button class="btn btn-ghost" type="button">Ghost</button>
		<button class="btn btn-sm" type="button">Piccolo</button>
		<button class="btn btn-danger" type="button"><Trash size={20} aria-hidden="true" /> Elimina</button>
		<button class="btn" type="button" disabled>Disabilitato</button>
	</p>
	<h3>Campi e filtri</h3>
	<div class="field">
		<label for="st-in">Titolo</label>
		<input id="st-in" type="text" value="Jazz in piazza" />
		<span class="hint">Suggerimento sotto il campo.</span>
	</div>
	<p class="row">
		<button class="chip" type="button" aria-pressed="false">Tutti</button>
		<button class="chip" type="button" aria-pressed="true">Musica</button>
		<button class="chip" type="button" aria-pressed="false">Sport</button>
	</p>
	<h3>Messaggi</h3>
	<p class="notice">Avviso neutro, senza colore.</p>
	<ErrorMessage>Errore con icona e testo, mai solo colore.</ErrorMessage>
	<h3>Elemento sovrapposto</h3>
	<div class="overlay-sample">
		<p><strong>Dialog, menu e toast</strong> sono gli unici con ombra: <code>--shadow-overlay</code>.</p>
	</div>
	<h3>Riga delle statistiche mensili</h3>
	<p class="num">{monthLine(412, 374, keys)}</p>
</section>

<style>
	.probe {
		position: absolute;
		visibility: hidden;
	}
	section {
		margin-top: var(--space-6);
	}
	.plain {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.space-row,
	.type-row {
		display: grid;
		grid-template-columns: var(--space-7) 1fr;
		align-items: center;
		gap: var(--space-3);
		padding-block: var(--space-1);
	}
	.bar {
		height: var(--space-3);
		background: var(--accent);
	}
	.swatches li {
		display: grid;
		grid-template-columns: var(--space-6) 1fr;
		gap: var(--space-1) var(--space-3);
		align-items: center;
		padding-block: var(--space-2);
		border-bottom: 1px solid var(--border);
	}
	.swatches li > :last-child {
		grid-column: 2;
		font-size: var(--text-sm);
	}
	.chipcolor {
		display: block;
		width: var(--space-6);
		height: var(--space-6);
		border: 1px solid var(--border-strong);
		border-radius: var(--radius-sm);
	}
	.grays {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-3);
	}
	.grays li {
		display: grid;
		justify-items: center;
		gap: var(--space-1);
	}
	.icon-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(var(--space-7), 1fr));
		gap: var(--space-3);
	}
	.icon-grid li {
		display: grid;
		justify-items: center;
		gap: var(--space-1);
		text-align: center;
		font-size: var(--text-xs);
	}
	.sizes {
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}
	.row {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
	}
	.num {
		font-variant-numeric: tabular-nums;
	}
	.overlay-sample {
		padding: var(--space-3);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--surface);
		box-shadow: var(--shadow-overlay);
	}
	code {
		font-size: var(--text-sm);
	}
</style>

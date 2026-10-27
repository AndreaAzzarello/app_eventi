<script lang="ts">
	import { onMount } from 'svelte';
	import FavoriteButton from '$lib/components/FavoriteButton.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import PinMap from '$lib/components/PinMap.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import { siteUrl } from '$lib/config';
	import { formatWhen } from '$lib/dates';
	import { CATEGORIES, PRICE_TYPES, cityPath, eventPath, isForKids, isFree, runningLabel } from '$lib/event';
	import { imageSources } from '$lib/images';
	import { buildIcs } from '$lib/ics';
	import { eventJsonLd, safeJson } from '$lib/jsonld';
	import { toast } from '$lib/toast.svelte';

	let { data } = $props();
	const e = $derived(data.event);
	const url = $derived(siteUrl() + eventPath(e));
	let now = $state(Date.now());
	onMount(() => (now = Date.now()));
	const running = $derived(runningLabel(e));
	const ended = $derived(e.endTime < now);
	const mapsUrl = $derived(`https://www.google.com/maps/search/?api=1&query=${e.lat},${e.lng}`);
	const description = $derived(
		e.shortDescription ||
			`${CATEGORIES[e.category]} a ${e.city || e.address}: ${formatWhen(e.startTime, e.endTime, now)}${e.venueName ? `, ${e.venueName}` : ''}.`
	);

	function sourceLabel(): { text: string; href?: string } {
		if (e.source === 'user') return { text: 'Segnalato da un utente e verificato dalla redazione' };
		if (!e.sourceUrl) return { text: 'Redazione di Eventi Vicini' };
		const host = new URL(e.sourceUrl).hostname.replace(/^www\./, '');
		const m = /^comune\.([a-z-]+)\./.exec(host);
		const name = m ? `Comune di ${m[1].split('-').map((w) => w[0].toUpperCase() + w.slice(1)).join(' ')}` : host;
		return { text: name, href: e.sourceUrl };
	}
	const source = $derived(sourceLabel());
	const jsonLdTag = $derived('<script type="application/ld+json">' + safeJson(eventJsonLd(e, url)) + '</' + 'script>');

	function downloadIcs() {
		const blob = new Blob([buildIcs(e, url)], { type: 'text/calendar;charset=utf-8' });
		const a = document.createElement('a');
		a.href = URL.createObjectURL(blob);
		a.download = `${eventPath(e).split('/').pop()}.ics`;
		a.click();
		setTimeout(() => URL.revokeObjectURL(a.href), 1000);
	}

	async function share() {
		if (navigator.share) {
			try {
				await navigator.share({ title: e.title, text: formatWhen(e.startTime, e.endTime), url });
			} catch {
				// condivisione annullata dall'utente
			}
			return;
		}
		try {
			await navigator.clipboard.writeText(url);
			toast('Link copiato negli appunti.');
		} catch {
			toast('Copia non riuscita: seleziona l’indirizzo dalla barra del browser.');
		}
	}
</script>

<Seo title={e.title} {description} image={e.imageUrl} type="article" path={eventPath(e)} />
<svelte:head>
	<!-- eslint-disable-next-line svelte/no-at-html-tags -- JSON-LD con < > & già codificati da safeJson -->
	{@html jsonLdTag}
</svelte:head>

<article class="container narrow detail">
	<a class="back" href="/"><Icon name="back" size={18} /> Tutti gli eventi</a>

	{#if ended}
		<p class="notice" role="note"><strong>Evento concluso.</strong> Lo lasciamo qui per memoria: cerca le prossime date in home.</p>
	{/if}

	{#if e.imageUrl}
		{@const img = imageSources(e.imageUrl)}
		<img
			class="hero"
			src={img.src}
			srcset={img.srcset}
			sizes="(min-width: 800px) 760px, 100vw"
			alt=""
			width="760"
			height="380"
			loading="eager"
			decoding="async"
			fetchpriority="high"
			referrerpolicy="no-referrer"
		/>
	{/if}

	<div class="tags">
		<span class="badge badge-brand">{CATEGORIES[e.category]}</span>
		{#if running}<span class="badge">{running}</span>{/if}
		<span class="badge" class:badge-free={isFree(e)}>{PRICE_TYPES[e.priceType]}</span>
		{#if isForKids(e) && e.category !== 'kids'}<span class="badge">Per bambini</span>{/if}
	</div>

	<h1>{e.title}</h1>

	<dl class="facts">
		<div>
			<dt><Icon name="calendar" /><span class="visually-hidden">Quando</span></dt>
			<dd class="when">{formatWhen(e.startTime, e.endTime, now)}</dd>
		</div>
		<div>
			<dt><Icon name="pin" /><span class="visually-hidden">Dove</span></dt>
			<dd>
				{#if e.venueName}<strong>{e.venueName}</strong><br />{/if}
				{#if e.approxLocation}<span class="approx">Luogo da confermare</span>{:else}{e.address}{/if}
				{#if e.locality && e.locality !== e.city}<br />{e.locality}, {e.city}{/if}
				{#if e.citySlug}<br /><a href={cityPath(e.citySlug)}>Altri eventi a {e.city}</a>{/if}
			</dd>
		</div>
	</dl>

	<div class="actions">
		<FavoriteButton id={e.id} title={e.title} label />
		{#if e.ticketUrl}
			<a class="btn btn-primary" href={e.ticketUrl} target="_blank" rel="noopener noreferrer nofollow">
				<Icon name="ticket" size={18} /> Biglietti
			</a>
		{/if}
		<button class="btn" onclick={downloadIcs}><Icon name="calendar" size={18} /> Aggiungi al calendario</button>
		<button class="btn" onclick={share}><Icon name="share" size={18} /> Condividi</button>
	</div>

	{#if e.shortDescription}
		<p class="desc">{e.shortDescription}</p>
	{/if}

	<section aria-labelledby="map-h" class="where">
		<div class="where-head">
			<h2 id="map-h">Come arrivare</h2>
			<a class="btn btn-sm" href={mapsUrl} target="_blank" rel="noopener noreferrer">
				<Icon name="external" size={16} /> Apri in Maps
			</a>
		</div>
		{#if e.approxLocation}
			<!-- Posizione solo al centro del comune: niente mappa, un pin preciso sarebbe falso. -->
			<p class="muted">Il luogo esatto non è ancora noto: verifica sul sito della fonte.</p>
		{:else}
			<PinMap lat={e.lat} lng={e.lng} label={`Mappa: ${e.venueName || e.address}`} />
		{/if}
	</section>

	<p class="source muted">
		Fonte:
		{#if source.href}<a href={source.href} target="_blank" rel="noopener noreferrer">{source.text}</a>{:else}{source.text}{/if}.
		Verifica sempre date e orari sul sito ufficiale prima di partire.
	</p>
</article>

<style>
	.detail {
		padding-top: 1rem;
	}
	.back {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		min-height: 44px;
		color: var(--muted);
		font-weight: 600;
		text-decoration: none;
	}
	.back:hover {
		color: var(--brand);
	}
	.notice {
		margin: 0.5rem 0 1rem;
	}
	.hero {
		width: 100%;
		height: auto;
		aspect-ratio: 2 / 1;
		object-fit: cover;
		border-radius: var(--radius);
		margin: 0.5rem 0 1.25rem;
		background: var(--surface-2);
	}
	.tags {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
		margin: 0.5rem 0 0.75rem;
	}
	h1 {
		overflow-wrap: anywhere;
	}
	.facts {
		display: grid;
		gap: 0.9rem;
		margin: 1.25rem 0;
	}
	.facts div {
		display: grid;
		grid-template-columns: 28px 1fr;
		gap: 0.6rem;
	}
	.facts dt {
		color: var(--brand);
		padding-top: 2px;
	}
	.facts dd {
		margin: 0;
	}
	.when {
		font-weight: 600;
		font-size: 1.08rem;
	}
	.when::first-letter {
		text-transform: uppercase;
	}
	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		margin: 1.25rem 0 1.5rem;
	}
	.desc {
		font-size: 1.08rem;
		line-height: 1.7;
		white-space: pre-line;
		overflow-wrap: anywhere;
	}
	.where {
		margin-top: 2rem;
	}
	.where-head {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 1rem;
		margin-bottom: 0.75rem;
	}
	.where-head h2 {
		margin: 0;
	}
	.approx {
		font-style: italic;
		color: var(--muted);
	}
	.source {
		margin-top: 1.5rem;
		font-size: 0.9rem;
	}
</style>

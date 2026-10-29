<script lang="ts">
	import { onMount } from 'svelte';
	import FavoriteButton from '$lib/components/FavoriteButton.svelte';
	import PinMap from '$lib/components/PinMap.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import { siteUrl } from '$lib/config';
	import { formatWhen, sentence } from '$lib/dates';
	import { CATEGORY_ICONS } from '$lib/categoryIcons';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import Calendar from '@lucide/svelte/icons/calendar';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import MapPin from '@lucide/svelte/icons/map-pin';
	import Share2 from '@lucide/svelte/icons/share-2';
	import Ticket from '@lucide/svelte/icons/ticket';
	import { CATEGORIES, PRICE_TYPES, cityPath, eventPath, eventSource, isForKids, runningLabel } from '$lib/event';
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

	const Cat = $derived(CATEGORY_ICONS[e.category]);
	const source = $derived(eventSource(e));
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
	<a class="back" href="/"><ArrowLeft size={20} aria-hidden="true" /> Tutti gli eventi</a>

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
		<span class="badge badge-cat"><Cat size={16} aria-hidden="true" /> {CATEGORIES[e.category]}</span>
		{#if running}<span class="badge">{running}</span>{/if}
		<span class="badge">{PRICE_TYPES[e.priceType]}</span>
		{#if isForKids(e) && e.category !== 'kids'}<span class="badge">Per bambini</span>{/if}
	</div>

	<h1>{e.title}</h1>

	<dl class="facts">
		<div>
			<dt><Calendar size={24} aria-hidden="true" /><span class="visually-hidden">Quando</span></dt>
			<dd class="when">{sentence(formatWhen(e.startTime, e.endTime, now))}</dd>
		</div>
		<div>
			<dt><MapPin size={24} aria-hidden="true" /><span class="visually-hidden">Dove</span></dt>
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
				<Ticket size={20} aria-hidden="true" /> Biglietti
			</a>
		{/if}
		<button class="btn" onclick={downloadIcs}><Calendar size={20} aria-hidden="true" /> Aggiungi al calendario</button>
		<button class="btn" onclick={share}><Share2 size={20} aria-hidden="true" /> Condividi</button>
	</div>

	{#if e.shortDescription}
		<p class="desc">{e.shortDescription}</p>
	{/if}

	<section aria-labelledby="map-h" class="where">
		<div class="where-head">
			<h2 id="map-h">Come arrivare</h2>
			<a class="btn btn-sm" href={mapsUrl} target="_blank" rel="noopener noreferrer">
				<ExternalLink size={16} aria-hidden="true" /> Apri in Maps
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
		padding-top: var(--space-3);
	}
	.back {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		min-height: var(--control);
		color: var(--muted);
		font-weight: var(--fw-strong);
		text-decoration: none;
	}
	.back:hover {
		color: var(--accent);
	}
	.notice {
		margin: var(--space-2) 0 var(--space-3);
	}
	.hero {
		width: 100%;
		height: auto;
		aspect-ratio: 2 / 1;
		object-fit: cover;
		border-radius: var(--radius);
		margin: var(--space-2) 0 var(--space-4);
		background: var(--surface-2);
	}
	.tags {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2) var(--space-3);
		margin: var(--space-2) 0 var(--space-3);
	}
	h1 {
		overflow-wrap: anywhere;
	}
	.facts {
		display: grid;
		gap: var(--space-3);
		margin: var(--space-4) 0;
	}
	.facts div {
		display: grid;
		grid-template-columns: var(--space-5) 1fr;
		gap: var(--space-2);
	}
	.facts dt {
		color: var(--muted);
	}
	.facts dd {
		margin: 0;
	}
	.when {
		font-weight: var(--fw-strong);
		font-size: var(--text-lg);
	}
	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
		margin: var(--space-4) 0;
	}
	.desc {
		font-size: var(--text-lg);
		line-height: var(--lh-body);
		white-space: pre-line;
		overflow-wrap: anywhere;
	}
	.where {
		margin-top: var(--space-5);
	}
	.where-head {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: var(--space-3);
		margin-bottom: var(--space-3);
	}
	.where-head h2 {
		margin: 0;
	}
	.approx {
		color: var(--muted);
	}
	.source {
		margin-top: var(--space-4);
		font-size: var(--text-sm);
	}
</style>

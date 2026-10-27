<script lang="ts">
	import { onMount } from 'svelte';
	import { compareEvents, type Event } from '$lib/event';
	import { favorites, session } from '$lib/session.svelte';
	import EventList from './EventList.svelte';

	let events = $state<Event[]>([]);
	let loading = $state(true);
	let error = $state('');
	let now = $state(Date.now());
	let loadedKey = '';

	// I dati arrivano da /api/events?ids= (cache all'edge), uguale per chi ha l'account e per chi no.
	async function load(ids: string[]) {
		const key = [...ids].sort().join(',');
		if (key === loadedKey) return;
		loadedKey = key;
		if (!ids.length) {
			events = [];
			loading = false;
			return;
		}
		loading = true;
		error = '';
		try {
			const res = await fetch(`/api/events?ids=${encodeURIComponent(key)}`);
			if (!res.ok) throw new Error();
			events = await res.json();
		} catch {
			error = 'Non riesco a caricare i preferiti.';
			loadedKey = '';
		} finally {
			loading = false;
		}
	}

	onMount(() => (now = Date.now()));
	$effect(() => {
		if (session.status === 'ready') load(favorites.ids);
	});

	// Togliere un preferito lo nasconde subito senza ricaricare.
	const shown = $derived(
		events.filter((e) => favorites.has(e.id)).sort((a, b) => (a.endTime < now ? 1 : 0) - (b.endTime < now ? 1 : 0) || compareEvents(now)(a, b))
	);
</script>

<EventList events={shown} {now} {loading} {error} onretry={() => ((loadedKey = ''), load(favorites.ids))}>
	{#snippet empty()}
		<h2>Ancora nessun preferito</h2>
		<p class="muted">Tocca il cuore su un evento per ritrovarlo qui.</p>
		<a class="btn btn-primary" href="/">Scopri gli eventi</a>
	{/snippet}
</EventList>

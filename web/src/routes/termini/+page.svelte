<script lang="ts">
	import Seo from '$lib/components/Seo.svelte';
	let { data } = $props();
</script>

<Seo title="Termini di utilizzo" description="Le regole per usare Eventi Vicini e proporre eventi." />

<article class="container narrow prose">
	<h1>Termini di utilizzo</h1>
	<p class="muted">Ultimo aggiornamento: {data.updated}</p>

	<h2>Il servizio</h2>
	<p>
		Eventi Vicini è un’agenda gratuita, offerta da {data.controller}, che raccoglie eventi pubblicati dai siti
		istituzionali dei Comuni (sempre citati come fonte), concerti e spettacoli dall’API di Ticketmaster e proposte degli utenti. Il servizio è fornito “così com’è”:
		facciamo il possibile perché le informazioni siano corrette, ma date, orari e prezzi possono cambiare.
		<strong>Verifica sempre sulla fonte ufficiale</strong> prima di partire.
	</p>

	<h2>Account</h2>
	<p>
		L’account è facoltativo e serve per conservare i preferiti e proporre eventi. Devi avere almeno 14 anni. Sei
		responsabile dell’uso del tuo account; puoi eliminarlo in qualsiasi momento da <a href="/account">Il mio account</a>.
	</p>

	<h2>Proporre un evento</h2>
	<ul>
		<li>Proponi solo eventi reali e aperti al pubblico, con informazioni corrette.</li>
		<li>Non inserire dati personali di terzi, contenuti offensivi, illegali o pubblicitari non pertinenti.</li>
		<li>Usa per le immagini solo link a contenuti che hai il diritto di condividere.</li>
		<li>Puoi avere al massimo 5 proposte in attesa di revisione.</li>
		<li>
			Ogni proposta viene revisionata: possiamo approvarla, modificarla o rifiutarla indicandone il motivo. Inviandola ci
			autorizzi a pubblicarla gratuitamente nell’agenda.
		</li>
	</ul>

	<h2>Responsabilità</h2>
	<p>
		Non organizziamo gli eventi elencati e non rispondiamo del loro svolgimento. I link esterni (biglietti, fonti)
		portano a siti di terzi con le proprie condizioni. I concerti e gli spettacoli sono forniti da Ticketmaster tramite la sua API: i biglietti si acquistano sul suo sito, alle sue condizioni, e Eventi Vicini non riceve commissioni né affiliazioni. Se Ticketmaster chiede di togliere un contenuto lo rimuoviamo entro 24 ore. Possiamo sospendere account che violano questi termini.
	</p>

	<h2>Modifiche e legge applicabile</h2>
	<p>
		Possiamo aggiornare questi termini: la data in alto indica l’ultima versione. Si applica la legge italiana.
		{#if data.email}Contatti: <a href="mailto:{data.email}">{data.email}</a>.{/if}
	</p>
	<p>Per il trattamento dei dati vedi l’<a href="/privacy">informativa privacy</a>.</p>
</article>

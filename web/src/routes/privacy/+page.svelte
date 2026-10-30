<script lang="ts">
	import Seo from '$lib/components/Seo.svelte';
	let { data } = $props();
</script>

<Seo title="Informativa privacy" description="Quali dati tratta Eventi Vicini, perché, per quanto tempo e con quali fornitori. Nessun tracciamento, nessuna pubblicità." />

<article class="container narrow prose">
	<h1>Informativa privacy</h1>
	<p class="muted">Ultimo aggiornamento: {data.updated}</p>

	<p>
		Eventi Vicini è un’agenda gratuita di eventi. Non usiamo analytics, pixel, pubblicità né cookie di profilazione:
		trattiamo solo i dati che servono a farti usare il servizio. Questa informativa è resa ai sensi degli artt. 13–14
		del Regolamento (UE) 2016/679 (GDPR).
	</p>

	<h2>Titolare del trattamento</h2>
	<p>
		Il titolare è {data.controller}.
		{#if data.email}Per qualsiasi richiesta scrivi a <a href="mailto:{data.email}">{data.email}</a>.{/if}
	</p>

	<h2>Quali dati e perché</h2>
	<ul>
		<li>
			<strong>Navigazione senza account.</strong> Non raccogliamo dati personali. La tua posizione (se la condividi o
			cerchi una città), i preferiti e il tema scelto restano <em>solo sul tuo dispositivo</em> (localStorage): non li
			salviamo sui nostri server. Per trovare gli eventi vicini il browser invia al server coordinate arrotondate a
			qualche chilometro, che non vengono registrate.
		</li>
		<li>
			<strong>Account (facoltativo).</strong> Se accedi con Google o con un link via email trattiamo: identificativo
			dell’account (uid), nome, indirizzo email, città preferita se la indichi, data di creazione, i tuoi preferiti e
			le proposte di evento che invii, con il loro stato.
		</li>
		<li>
			<strong>Proposte di evento.</strong> I dati dell’evento (titolo, luogo, date, link) vengono pubblicati se approvati.
			Chi ha proposto l’evento non viene mai mostrato pubblicamente.
		</li>
		<li>
			<strong>Dati tecnici.</strong> I fornitori qui sotto trattano l’indirizzo IP e dati di connessione per consegnare le
			pagine e proteggere il servizio da abusi.
		</li>
	</ul>

	<h2>Base giuridica</h2>
	<p>
		Il trattamento è necessario per eseguire il servizio che richiedi (art. 6.1.b GDPR): mostrarti gli eventi,
		conservare i tuoi preferiti, gestire le tue proposte. I dati tecnici di sicurezza si basano sul legittimo interesse
		a mantenere il servizio sicuro e funzionante (art. 6.1.f).
	</p>

	<h2>Per quanto tempo</h2>
	<ul>
		<li>Dati dell’account, preferiti e proposte: finché non elimini l’account. Puoi farlo in ogni momento da <a href="/account">Il mio account</a> → “Elimina account e dati”: cancelliamo profilo, preferiti, proposte e l’account di accesso.</li>
		<li>Account inattivi da oltre 24 mesi possono essere eliminati.</li>
		<li>Gli eventi approvati restano pubblicati come contenuto dell’agenda, senza alcun riferimento visibile a chi li ha proposti.</li>
		<li>Dati sul tuo dispositivo: finché non li cancelli dalle impostazioni del browser.</li>
	</ul>

	<h2>Fornitori e trasferimenti</h2>
	<ul>
		<li><strong>Google Firebase</strong> (Google LLC / Google Ireland Ltd): autenticazione e database. Responsabile del trattamento.</li>
		<li><strong>Cloudflare, Inc.</strong>: hosting e consegna delle pagine. Responsabile del trattamento.</li>
		<li>
			<strong>OpenStreetMap Foundation</strong> (Regno Unito): le tessere della mappa sono scaricate direttamente dal tuo
			browser; la ricerca di luoghi (Nominatim) passa dal nostro server, quindi Nominatim non riceve il tuo indirizzo IP.
		</li>
	</ul>
	<p>
		Google e Cloudflare possono trattare dati negli Stati Uniti: il trasferimento è coperto dall’EU-US Data Privacy
		Framework, a cui entrambe le società aderiscono, e dalle clausole contrattuali standard. Per il Regno Unito vale la
		decisione di adeguatezza della Commissione europea.
	</p>

	<h2>Siti di terzi e biglietti</h2>
	<p>
		Alcuni eventi (concerti e spettacoli) arrivano dall’API pubblica di Ticketmaster, che ne è la fonte. Il pulsante
		“Acquista i biglietti” e i link alle fonti sono semplici collegamenti: finché non li apri non inviamo nulla a terzi e
		non carichiamo script di Ticketmaster. L’unico contatto prima del clic sono le immagini degli eventi, che il tuo
		browser scarica dai server di Ticketmaster (come per ogni immagine di una fonte esterna, il server che la
		fornisce vede il tuo indirizzo IP). Dopo il clic sei sul sito del venditore, che può impostare i propri cookie e
		trattare i tuoi dati con la propria informativa. Non riceviamo commissioni e non
		sappiamo se acquisti.
	</p>

	<h2>Cookie e archiviazione locale</h2>
	<p>
		Usiamo solo archiviazione tecnica: preferiti, posizione, tema, e la sessione di accesso di Firebase. Nessun cookie
		di terze parti per pubblicità o statistiche sul nostro sito (quelli dei siti a cui rimandiamo nascono solo dopo il clic), per questo non vedi banner. Se in futuro attivassimo statistiche,
		useremmo Cloudflare Web Analytics, che non usa cookie né identifica i visitatori.
	</p>

	<h2>I tuoi diritti</h2>
	<p>
		Puoi chiedere accesso, rettifica, cancellazione, limitazione, portabilità dei dati e opporti al trattamento
		(artt. 15–22 GDPR){#if data.email}, scrivendo a <a href="mailto:{data.email}">{data.email}</a>{/if}. Puoi anche proporre
		reclamo al <a href="https://www.garanteprivacy.it" rel="noopener">Garante per la protezione dei dati personali</a>.
	</p>

	<h2>Età minima</h2>
	<p>Per creare un account devi avere almeno 14 anni (art. 2-quinquies del Codice privacy).</p>
</article>

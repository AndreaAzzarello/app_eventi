# Bozza di email al Consorzio dei Comuni Trentini

Da inviare dalla tua casella (nessuna richiesta all'API ComunWEB è stata fatta oltre alle tre di prova descritte nel testo). Completa i campi tra parentesi quadre.

**A**: [indirizzo del Consorzio dei Comuni Trentini, per esempio dalla pagina contatti di https://www.comunitrentini.it]
**Oggetto**: Richiesta di autorizzazione alla lettura via API degli eventi dei Comuni trentini (progetto gratuito, senza pubblicità)

---

Gentili referenti del Consorzio dei Comuni Trentini,

mi chiamo Andrea Azzarello e sviluppo "Eventi Vicini" (https://eventi-vicini.pages.dev), una webapp gratuita che aiuta a trovare gli eventi pubblici vicini a sé: concerti, sagre, mostre, mercatini, attività per bambini. Il progetto è senza scopo di lucro, senza pubblicità e senza raccolta di dati personali a fini commerciali; il codice è pubblico (https://github.com/AndreaAzzarello/app_eventi).

Gli eventi sono letti dai siti istituzionali dei Comuni. Molti Comuni trentini usano la piattaforma ComunWEB, che espone un'API di ricerca dei contenuti (`/api/opendata/v2/content/search/`). Il file robots.txt di questi siti però esclude il percorso `/api/`, quindi non la uso e non intendo usarla senza un vostro consenso esplicito.

Vi chiedo gentilmente:

1. il permesso di leggere, tramite quell'API, i soli contenuti di tipo evento dei siti ComunWEB dei Comuni trentini;
2. a quali condizioni d'uso e con quale licenza sono riutilizzabili i dati degli eventi (per esempio CC-BY 4.0);
3. se esiste un feed degli eventi, un'API alternativa o una chiave di accesso a voi preferibile, e quale classe di contenuto devo interrogare (sui siti che ho provato la classe `evento` non esiste);
4. se potete indicare nel robots.txt un'eccezione per il mio User-Agent.

Mi impegno a:

- fare al massimo 1 richiesta al secondo per sito, con un solo ciclo di lettura al giorno e con cache delle risposte non modificate;
- identificarmi con lo User-Agent `EventiVicini-importer/1.0 (+https://github.com/AndreaAzzarello/app_eventi)`;
- leggere solo gli eventi futuri, senza dati personali;
- citare sempre la fonte, con il nome del Comune e il collegamento alla pagina originale dell'evento;
- sospendere subito la lettura e rimuovere i dati a una vostra semplice richiesta.

Per trasparenza: durante una verifica tecnica ho inviato tre richieste di prova all'endpoint `/api/opendata/v2/content/search/` di tre siti (Cles, Arco, Pergine Valsugana), una per sito, prima di aver letto il robots.txt. Appena letto il file mi sono fermato e non ne ho fatte altre.

Resto a disposizione per qualsiasi chiarimento e vi ringrazio per l'attenzione.

Cordiali saluti,
Andrea Azzarello
[email di contatto]

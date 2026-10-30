# Bozza di email ai fornitori di siti comunali che bloccano i bot in robots.txt

Da inviare dalla tua casella, una volta per fornitore. Completa i campi tra parentesi quadre.

Caso noto: in Lombardia circa 405 siti comunali rispondono con `server: HGATE` e un `robots.txt` che vieta tutto (`Disallow: /`) a ogni bot tranne Googlebot (verificato su comune.arzago.bg.it il 28/10/2026, una sola richiesta). Il fornitore dietro "HGATE" **non è stato identificato** da fonti pubbliche (ricerca del 30/10/2026: nessuna fonte collega HGATE a un fornitore; il robots.txt non contiene nomi né contatti). Prima di scrivere chiedi al Comune con `email_comune_robots.md`, poi sostituisci [fornitore]. Non ho inventato nessun indirizzo.

**A**: [indirizzo del fornitore]
**Oggetto**: Richiesta di eccezione nel robots.txt per un progetto gratuito di calendario eventi dei Comuni

---

Gentili referenti di [fornitore],

mi chiamo Andrea Azzarello e sviluppo "Eventi Vicini" (https://eventi-vicini.pages.dev), una webapp gratuita che aiuta a trovare gli eventi pubblici vicini a sé. È senza scopo di lucro e senza pubblicità; il codice è pubblico (https://github.com/AndreaAzzarello/EventiVicini).

I siti dei Comuni che gestite hanno un robots.txt che vieta l'accesso a tutti i bot (`Disallow: /`). Rispetto quel divieto e per questo non leggo quei siti. Vi chiedo se sia possibile ammettere, almeno per le pagine pubbliche degli eventi, il mio User-Agent, oppure indicarmi un feed o un'API che preferite.

Mi impegno a:

- fare al massimo 1 richiesta al secondo per sito, un solo ciclo di lettura al giorno, con cache delle pagine non modificate;
- identificarmi con lo User-Agent `EventiVicini-importer/1.0 (+https://github.com/AndreaAzzarello/EventiVicini)`;
- leggere solo gli eventi futuri, senza dati personali;
- citare sempre il Comune e il collegamento alla pagina originale;
- sospendere subito la lettura e rimuovere i dati a una vostra richiesta.

Grazie per l'attenzione e per il lavoro che fate per i Comuni.

Cordiali saluti,
Andrea Azzarello
[email di contatto]

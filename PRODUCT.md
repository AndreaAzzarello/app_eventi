# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

# Eventi Vicini: brief di prodotto

## Cos'è
Eventi Vicini è un'agenda locale degli eventi pubblici italiani (fonti: siti dei Comuni e open data), gratuita, senza pubblicità né tracciamento.

## Chi la usa
Persone del posto, famiglie con bambini, turisti. Soprattutto da telefono, spesso all'ultimo momento.

## La domanda a cui risponde
"Cosa faccio stasera / questo weekend, qui vicino?"
In 3 secondi l'utente deve capire:
- QUANDO
- DOVE (e quanto è lontano)
- QUANTO COSTA
- SE VA BENE PER I BAMBINI

## I dati
Sono disomogenei: molti eventi senza immagine, orari "tutto il giorno", luoghi approssimati ("luogo da confermare"), mostre lunghe. Il design deve far sembrare curati anche questi casi.

## Personalità
Un'agenda culturale italiana stampata: manifesti, piazze, mattoni, carta calda. Affidabile perché basata su fonti pubbliche. Calda, editoriale, viva. Non una dashboard, non una startup tech, non un template.

## Obiettivo della rifinitura
Un design accattivante e memorabile, non piatto, mantenendo ordine e accessibilità.

## Direzione di design
1. **Struttura per tempo**: in home la lista è divisa in sezioni "Oggi", "Stasera" (dalle 18), "Questo weekend", "Prossimi giorni", "In corso" (mostre e rassegne longRunning, compatte in fondo). Titoli di sezione in Fraunces. Filtri e mappa restano funzionanti.
2. **Card "biglietto/manifesto"**: blocco data riconoscibile (giorno grande in Fraunces, mese e giorno della settimana piccoli, fondo tinta della categoria), titolo forte, una riga di fatti chiave con icone (ora o "tutto il giorno", luogo · distanza, prezzo, adatto ai bambini). Con immagine: proporzione fissa, object-fit, lazy, srcset. Senza: placeholder disegnato per categoria (motivo geometrico SVG nella tinta della categoria e icona grande), mai un riquadro vuoto o grigio.
3. **Colore**: la terracotta resta l'accento per azioni e stato attivo. Palette di categoria a toni naturali italiani (musica prugna, cibo ocra, cultura verde acqua, sport oliva, bambini corallo tenue, mercati sabbia, altro grigio caldo), usata solo come tinta tenue (fondi del blocco data, placeholder, marker, chip), con testo sempre in contrasto AA nei due temi. Sfondo "carta calda" nel tema chiaro, "notte calda" nel tema scuro.
4. **Home con identità**: testata con il titolo "Cosa succede vicino a te" (corsivo terracotta su "vicino a te"), sotto la riga del luogo e la barra di ricerca; sfondo discreto (texture SVG leggerissima o motivo a tratti), senza appesantire la performance.
5. **Mappa intonata**: tile OSM con filtro CSS per toni caldi e desaturati (verificare la leggibilità), marker a goccia con colore e icona della categoria, cluster numerati quando sono vicini, card di anteprima al tocco del marker.
6. **Dettaglio evento**: testata con immagine o placeholder di categoria, blocco "in breve" (quando, dove con distanza, prezzo, bambini, fonte), azioni principali ben visibili (Aggiungi al calendario, Indicazioni, Condividi), "Luogo da confermare" presentato con garbo e link alla fonte.
7. **Microinterazioni sobrie**: hover e press delle card (sollevamento leggero con ombra in token), transizione morbida lista/mappa, skeleton con la forma delle card, rispetto di `prefers-reduced-motion`.
8. **Testi**: microcopy caldo e umano in italiano per stati vuoti, errori e conferme (es. "Stasera qui è tranquillo. Prova ad allargare la distanza o guarda il weekend.").
9. **Filtri**: niente "Bambini" doppio (resta il filtro rapido), categorie nella stessa riga che scorre in orizzontale, così la barra resta bassa su mobile. Un link condiviso senza `?luogo=` non mostra mai eventi di un luogo scelto a caso: il server mostra la scelta del luogo e i link alle regioni e città con più eventi.

## Regole di base (da DESIGN.md)
Scala di spaziature, icone Lucide, niente gradienti né glow, niente maiuscolo, contrasti AA, due pesi (400/600).

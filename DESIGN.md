# Design system

Fonte di verità dei valori: `web/src/lib/styles/tokens.css` (un solo file di token). Riferimento visivo: `/admin/stile` (colori misurati nel tema in uso, tipografia, icone, componenti). Le regole sono imposte da `web/src/lib/styles/design.test.ts`.

## Prima di modificare il frontend
- Solo token: niente misure assolute, esadecimali o `rgb()` nel CSS dei componenti.
- Pesi solo 400 e 600; icone solo Lucide; `--danger` solo con icona e testo (`ErrorMessage.svelte` o `.btn-danger`).
- Verifica: `npm test` in `web/` (include `design.test.ts`) e controllo visivo a 360 px.

## Regole
- **Spaziatura**: `--space-1..7` = 4, 8, 16, 24, 32, 48, 64 px. Raggi `--radius-sm/--radius/--radius-full`, controlli `--control` (48) e `--control-sm` (32). Nel CSS dei componenti non ci sono misure assolute (ammessi solo 0, 1px, 2px per filetti e outline).
- **Colore**: dieci grigi caldi (`--gray-50..900`) e un solo accento, il terracotta (`--accent`), per azioni primarie, link, focus e stato attivo. L'errore (`--danger`, cremisi) si usa solo con icona e testo, tramite `ErrorMessage.svelte` o `.btn-danger`. Tema chiaro e scuro con `light-dark()` in un solo blocco; `data-theme` lo forza. Niente gradienti, glow o ombre colorate: l'unica ombra è `--shadow-overlay` (dialog, menu, toast). **Unica eccezione ai colori**: la "G" ufficiale a quattro colori di "Accedi con Google" (`lib/components/GoogleLogo.svelte`), richiesta dalle linee guida di Google; il test di design ammette solo quel file e solo i quattro colori ufficiali.
- **Tipografia**: pesi 400 e 600, scala `--text-xs..3xl`; Fraunces 600 (un solo file) per i titoli. Mai maiuscolo forzato.
- **Icone**: solo Lucide (`@lucide/svelte`, import per singola icona), 16/20/24, tratto 2. Le categorie hanno un'icona (`lib/categoryIcons.ts`), non un colore.
- **Numeri**: `fmtNum()` (`lib/format.ts`), formato italiano 1.234, `tabular-nums` dove sono allineati.
- **Controllo automatico**: `web/src/lib/styles/design.test.ts` (parte di `npm test` e della CI) fallisce per misure fuori scala, esadecimali/rgb fuori dai token, `font-weight` diversi da 400/600, `text-transform: uppercase|capitalize`, gradienti, `backdrop-filter`, emoji, `var(--danger)` fuori dai file ammessi; verifica anche contrasto WCAG AA di ogni coppia testo/sfondo in entrambi i temi e che l'errore sia lontano almeno 25° di tinta dall'accento.
- **Screenshot di revisione**: `REVIEW_SHOTS=before|after` con `playwright test review-shots` (dentro `emulators:exec`, come `test:e2e`) salva home, città, regione, dettaglio e admin a 360, 390 e desktop, in chiaro e scuro, in `web/.review/<valore>/` (non committata). `REVIEW_VIEWS=<cartella>` con `review-views` fotografa accedi, proponi, account e tutte le viste admin (360 e desktop, due temi, anche il dialog di eliminazione e gli errori del form).
- **Header stretto**: sotto i 480 px "Proponi" (nel footer) e "Admin" (nella pagina account) escono dall'header, così il marchio resta intero a 360 px (test in `e2e/layout-mobile.spec.ts`).

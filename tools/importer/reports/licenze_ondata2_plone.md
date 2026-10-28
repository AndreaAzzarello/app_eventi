# Licenze dei contenuti: comuni Emilia-Romagna

## Metodo

- Per ogni comune (candidati WordPress/Plone più Modena, Formigine, Sassuolo, Mirandola) lo script `licenses.py` scarica la home e cerca i link a note legali, termini d'uso, condizioni d'uso, licenza, privacy (anche nel piè di pagina) e prova percorsi tipici (`/note-legali`, `/it/note-legali`, `/privacy`, `/amministrazione-trasparente`...).
- Dalle pagine estrae la frase testuale che nomina CC-BY / Creative Commons / licenza (max 300 caratteri, riportata senza modifiche).
- Classe: `contenuti` (la licenza riguarda testi, dati, immagini del sito), `solo-software` (riguarda tema, codice, design system), `non-chiara`, `non-trovata`. La classificazione è euristica sulle parole della frase: le `contenuti` vanno comunque lette.
- Robots (protego, UA `EventiVicini-importer/1.0 (+https://github.com/AndreaAzzarello/app_eventi)`): pagina eventi e percorso API usato dall'adapter (Plone `/++api++/@search`, WordPress `/wp-json/wp/v2/`).
- Regola: **attivare** solo se la frase attesta licenza aperta sui CONTENUTI e robots permette l'API; **escludere** se robots vieta o la licenza è restrittiva; altrimenti **da verificare a mano**. Nessuno `stato` è stato modificato.

## Riepilogo

- Comuni analizzati: 3
- Raccomandazione: da verificare a mano 2, attivare 1
- Classe licenza: non-trovata 2, contenuti 1

## Tabella

| comune | CMS | licenza | frase (pagina) | robots | raccomandazione |
|---|---|---|---|---|---|
| Pordenone | plone | non trovata | 4 pagine controllate, nessuna frase sulla licenza | eventi: si; API: si | da verificare a mano |
| Lignano Sabbiadoro | plone | non trovata | 5 pagine controllate, nessuna frase sulla licenza | eventi: si; API: si | da verificare a mano |
| La Spezia | plone | CC-BY-4.0 | «n applicazione del principio open by default ai sensi dell’articolo 52 del decreto legislativo 7 marzo 2005, n. 82 (CAD) e salvo dove diversamente specificato (compresi i contenuti incorporati di terzi), i dati, i documenti e le informazioni pubblicati sul sito sono rilasciati con licenza CC-BY 4.0.» (https://www.comune.laspezia.it/note-legali) | eventi: si; API: si | attivare |

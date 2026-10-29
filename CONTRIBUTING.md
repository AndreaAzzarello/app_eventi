# Contribuire

Grazie dell'interesse. Il progetto è piccolo e gratuito per scelta: le modifiche devono restare nei vincoli di [`CLAUDE.md`](CLAUDE.md) (Firebase Spark, nessun servizio a pagamento, nessun tracciamento).

## Setup

Vedi [docs/sviluppo.md](docs/sviluppo.md). In breve: Node 24, JDK 21, Python 3.12, `npm install` in `web/` e `firebase/`.

## Prima di aprire una pull request

```powershell
cd web; npm run check; npm run lint; npm test; npm run build
cd ..\firebase; npm test                      # se tocchi le regole
cd ..\tools\importer; python -m pytest -q tests   # se tocchi l'importer
```

- Frontend: leggi [`DESIGN.md`](DESIGN.md); i valori stanno in `web/src/lib/styles/tokens.css` e il controllo in `design.test.ts`.
- Un commit per modifica, con messaggio chiaro (in italiano, come la cronologia).
- Non committare `.env`, `.dev.vars`, chiavi di service account.
- Non modificare a mano `sources/*.csv` e `reports/`: passano dagli script (`activate.py`, `licenses.py`).

## Proporre una nuova fonte comunale

Apri una issue con:

1. comune, provincia e sito istituzionale;
2. URL della pagina degli eventi;
3. la frase delle note legali che indica la licenza dei contenuti (serve CC0 o CC-BY);
4. cosa dice il `robots.txt` per la pagina eventi e per l'eventuale API.

Poi si procede così (comandi in [docs/importer.md](docs/importer.md)): `detect_cms.py` riconosce il CMS, `licenses.py` verifica la licenza, `activate.py` attiva la fonte solo se rispetta tutte le condizioni (adapter, licenza, robots.txt, almeno un evento futuro valido). Siti con licenza restrittiva o che vietano l'accesso nel `robots.txt` non si attivano. Un CMS senza adapter richiede un nuovo adapter con test su fixture salvate.

## Segnalare problemi

Bug e idee: issue pubbliche. Vulnerabilità: vedi [SECURITY.md](SECURITY.md).

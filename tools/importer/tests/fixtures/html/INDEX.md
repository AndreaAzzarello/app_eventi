# Fixture HTML per l'importer

Generate con fetch.Fetcher (robots.txt rispettato, 1 req/s per host, UA del progetto), senza cache su disco.
Ogni comune: lista.html, dettaglio-1.html, dettaglio-2.html (UTF-8).
Pulizia: rimossi i blocchi <style>, <svg> e <script> senza ld+json; il resto invariato.
Richieste: 69 in totale (60 primo giro + 9 secondo giro), sopra il budget di ~60 per cercare fornitori diversi.

| slug | url lista | url dettagli | CMS/fornitore stimato | byte |
|---|---|---|---|---|
| bagno-di-romagna | https://www.comune.bagnodiromagna.fc.it/vivere-il-comune/eventi/ | https://www.comune.bagnodiromagna.fc.it/vivere-il-comune/eventi/conoscere-le-erbe-e-gustarle/ ; https://www.comune.bagnodiromagna.fc.it/vivere-il-comune/eventi/passaggi-di-primavera/ | WordPress (Design Comuni Italia); Bootstrap Italia | lista 68784, dettaglio-1 94186, dettaglio-2 96891 |
| mercato-saraceno | https://www.comune.mercatosaraceno.fc.it/vivere-il-comune/eventi/ | https://www.comune.mercatosaraceno.fc.it/vivere-il-comune/eventi/la-salute-mentale-sale-sul-palco-a-palazzo-dolcini-arriva-disturbo-della-compagnia-il-garbuglio-aps/ ; https://www.comune.mercatosaraceno.fc.it/vivere-il-comune/eventi/torna-la-festa-del-patrono-a-mercato-saraceno-il-programma-dell8-settembre/ | WordPress (Design Comuni Italia); Bootstrap Italia | lista 73633, dettaglio-1 95875, dettaglio-2 107804 |
| montiano | https://www.comune.montiano.fc.it/vivere-il-comune/eventi/ | https://www.comune.montiano.fc.it/vivere-il-comune/eventi/sagra-del-cicciolo/ ; https://www.comune.montiano.fc.it/vivere-il-comune/eventi/pilates-al-parco/ | WordPress (Design Comuni Italia); Bootstrap Italia | lista 66450, dettaglio-1 79867, dettaglio-2 78911 |
| sarsina | https://www.comune.sarsina.fc.it/vivere-il-comune/eventi/ | https://www.comune.sarsina.fc.it/vivere-il-comune/eventi/ludi-plautini-sarsinates-viii-sarsina-24-ottobre-2026/ ; https://www.comune.sarsina.fc.it/vivere-il-comune/eventi/prendiamola-con-filosofia/ | WordPress (Design Comuni Italia); Bootstrap Italia | lista 68679, dettaglio-1 87132, dettaglio-2 85182 |
| verghereto | https://www.comune.verghereto.fc.it/vivere-il-comune/eventi/ | https://www.comune.verghereto.fc.it/vivere-il-comune/eventi/sagra-della-castagna-domenica-12-ottobre-e-domenica-19-ottobre-pro-loco-alfero/ ; https://www.comune.verghereto.fc.it/vivere-il-comune/eventi/festa-di-santalberico-pro-loco-capanne/ | WordPress (Design Comuni Italia); Bootstrap Italia | lista 66553, dettaglio-1 81041, dettaglio-2 80810 |
| granarolo-dell-emilia | https://www.comune.granarolo-dellemilia.bo.it/it-it/vivere-il-comune/eventi | https://www.comune.granarolo-dellemilia.bo.it/it-it/vivere-il-comune/eventi/la-scuola-di-pozioni-un-laboratorio-di-halloween-alla-biblioteca-rodari-132152-1-4dc81f467ec28eacde60a1682642f346 ; https://www.comune.granarolo-dellemilia.bo.it/it-it/vivere-il-comune/eventi/il-coraggio-di-essere-se-stessi-reading-per-bambine-bambini-e-ragazzi-con-elena-musti-132351-1-495703b35bd4f8474e937359332ad0ee | ComWeb (www.epublic.it); Bootstrap Italia | lista 72626, dettaglio-1 60958, dettaglio-2 62144 |
| casina | https://www.comune.casina.re.it/vivere-il-comune/eventi/ | https://www.comune.casina.re.it/vivere-il-comune/eventi/martedi-alla-cantoniera-paullo-reggiano-storia-famiglie-persone-immagini/ ; https://www.comune.casina.re.it/vivere-il-comune/eventi/lombra-che-resta-4/ | WordPress 7.1.3 (non DCI); Bootstrap Italia | lista 68611, dettaglio-1 72624, dettaglio-2 80804 |
| pavullo-nel-frignano | https://www.comune.pavullo-nel-frignano.mo.it/evento/ | https://www.comune.pavullo-nel-frignano.mo.it/evento/salone-dellorientamento-2026/ ; https://www.comune.pavullo-nel-frignano.mo.it/evento/insieme-che-festa-nati-per-leggere-14-21-novembre-2026/ | WordPress 6.8.11 (non DCI); Bootstrap Italia | lista 59888, dettaglio-1 58120, dettaglio-2 58254 |
| medicina | https://www.comune.medicina.bo.it/vivere-medicina/eventi | https://www.comune.medicina.bo.it/evento/2026-10-27-tra-un-caffe-e-l-altro ; https://www.comune.medicina.bo.it/evento/2026-10-27-pensare-francesco-storia-memoria-e-uso-politico | ASP.NET WebForms (fornitore non identificato); Bootstrap Italia | lista 167941, dettaglio-1 106088, dettaglio-2 108613 |

## Non salvati

- Masi Torello [A]: la lista ha un solo link a evento (serve il secondo)
- Voghiera [A]: nessun link a evento nella lista
- Cadeo [B]: nessun link a evento nella lista
- Fiumalbo [B]: la lista ha un solo link a evento (serve il secondo)
- Collecchio [B]: nessun link a evento nella lista
- Longiano [B]: nessun link a evento nella lista (dopo il filtro per slug)
- Soragna [B]: nessun link a evento nella lista
- Polinago [B]: nessun link a evento nella lista
- Alfonsine [B]: i link sono pagine di categoria (eZ Publish/OpenPA), non eventi; cartella rimossa
- Campione B: 12 candidati provati (non ~25) per il limite di richieste; fornitori diversi trovati: 3 (ComWeb, WordPress, ASP.NET), WordPress due volte
| riccione | https://www.comune.riccione.rn.it/it/events | https://www.comune.riccione.rn.it/it/events/il-parco-delle-zucche-la-magia-dell-autunno-a-villa-lodi-fe ; https://www.comune.riccione.rn.it/it/events/mostra-vissi-d-arte-da-un-sogno-una-storia | Municipium (Maggioli); Bootstrap Italia | aggiunta a mano dopo il controllo a campione |

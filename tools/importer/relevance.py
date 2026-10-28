"""Filtro anti-avvisi: pagine dei siti comunali che non sono eventi pubblici (sedute, avvisi, riepiloghi, titoli generici).

Funzione pura sul titolo; il controllo strutturale (pagina riassuntiva con molti link ad altri eventi e nessuna data
singola) sta in adapters/design_comuni_html.py e segnala con lo stesso formato di motivo.
"""

from __future__ import annotations

import re

from mapping import _norm

#: titoli che da soli non dicono nulla (confronto sul titolo normalizzato, senza accenti né punteggiatura)
GENERIC_TITLES = {
    "evento", "eventi", "evento culturale", "evento sportivo", "evento musicale", "evento gastronomico",
    "evento pubblico", "mostra", "spettacolo", "manifestazione", "iniziativa", "iniziative", "appuntamento",
}

#: pagine riassuntive: "Tutti gli eventi", "Eventi 2026", "Programma eventi estate", "Calendario eventi"
SUMMARY_RE = re.compile(
    r"^(?:tutti gli )?eventi(?: (?:in programma|del comune|di (?:\w+ ){0,2}20\d\d))?(?: 20\d\d)?$"
    r"|^(?:programma|calendario|elenco)\b.*\beventi\b"
    r"|^eventi\b.*\b(?:programma|calendario)\b"
    r"|^programma (?:dell |della )?(?:estate|estivo|autunno|inverno|primavera)\b"
    r"|^(?:estate|autunno|inverno|primavera) 20\d\d$")

#: sedute degli organi comunali
SEDUTA_RE = re.compile(
    r"\b(?:sedut[ae]|convocazion[ei]|riunion[ei])\b.*\b(?:consigli\w*|giunta|commission\w*)\b"
    r"|\b(?:consiglio|giunta)\s+(?:comunale|municipale)\b|\bcommissione\s+consiliare\b")

#: avvisi alla cittadinanza; si salvano se il titolo dice che è un incontro pubblico (EVENT_WORD_RE)
NOTICE_RE = re.compile(
    r"\brifiuti\b|\becocentro\b|\braccolta\s+(?:differenziata|porta)|\bingombranti\b"
    r"|\b(?:attenzione|allerta|avviso|tentativi?|false?)\b.*\btruff\w*|\btruff\w*\b.*\b(?:in corso|anziani)\b|\braggir\w*"
    r"|\ballert[ae]\b|\bavviso\b|\bavvisi\b"
    r"|\bpeste\s+suina\b|\binfluenza\s+aviaria\b|\bzanzara\s+tigre\b"
    r"|\bband[oi]\b|\bgraduatoria\b"
    r"|\bsicurezza\s+stradale\b|\bchiusura\s+(?:al\s+traffico|strada|ufficio|uffici)\b|\bviabilit[aà]\b"
    r"|\bsciopero\b|\binterruzione\s+(?:acqua|energia|servizio)\b")
EVENT_WORD_RE = re.compile(
    r"\b(?:incontro|conferenza|serata|convegno|laboratori\w*|corso|spettacol\w*|concert\w*|mostra|cerimonia|festa|"
    r"presentazione|assemblea|passeggiata|visita|giornata|workshop|evento)\b")

#: "Video: ..." come titolo di servizio
VIDEO_RE = re.compile(r"^video\b|\bvideo\s+(?:messaggio|istituzionale|del sindaco|integrale)\b|\bdiretta\s+streaming\b")


def exclusion_reason(title: str) -> str | None:
    """Motivo per cui la pagina non è un evento pubblico, None se va importata."""
    t = _norm(title)
    if not t:
        return None
    if t in GENERIC_TITLES:
        return "titolo generico"
    if SUMMARY_RE.search(t):
        return "pagina riassuntiva"
    if SEDUTA_RE.search(t):
        return "seduta di consiglio/giunta"
    if VIDEO_RE.search(t):
        return "video"
    if NOTICE_RE.search(t) and not EVENT_WORD_RE.search(t):
        return "avviso"
    return None

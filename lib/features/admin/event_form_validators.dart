/// Validatori puri del form admin: restituiscono il messaggio d'errore o null.
String? validateRequired(String? v, {int max = 200}) {
  final s = v?.trim() ?? '';
  if (s.isEmpty) return 'Campo obbligatorio';
  if (s.length > max) return 'Massimo $max caratteri';
  return null;
}

/// Vuoto è valido; altrimenti serve un link http(s) completo.
String? validateOptionalUrl(String? v) {
  final s = v?.trim() ?? '';
  if (s.isEmpty) return null;
  final u = Uri.tryParse(s);
  if (u == null || !(u.isScheme('https') || u.isScheme('http')) || u.host.isEmpty) {
    return 'Inserisci un link che inizi con https://';
  }
  return null;
}

String? validateRange(DateTime start, DateTime end) =>
    end.isBefore(start) ? 'La fine deve essere dopo l\'inizio' : null;

/// 0,0 è il default di Event.fromMap: significa "coordinate mancanti".
String? validateCoords(double? lat, double? lng) =>
    lat == null || lng == null || (lat == 0 && lng == 0)
        ? 'Imposta la posizione con "Trova coordinate" o toccando la mappa'
        : null;

/// "Live, outdoor , ,kids" → [live, outdoor, kids], minuscoli e senza doppioni.
List<String> parseTags(String raw) => {
      for (final t in raw.split(','))
        if (t.trim().isNotEmpty) t.trim().toLowerCase(),
    }.toList();

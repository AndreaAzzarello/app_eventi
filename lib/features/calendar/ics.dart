import '../events/domain/event.dart';

/// Genera un file iCalendar (RFC 5545) con un solo evento.
// shortcut: niente line folding a 75 ottetti, aggiungerlo se un client rifiuta descrizioni lunghe.
String buildIcs(Event e, {DateTime? now}) {
  String utc(DateTime d) {
    final s = d.toUtc().toIso8601String().replaceAll(RegExp(r'[-:]'), '');
    return '${s.split('.').first.replaceAll('Z', '')}Z';
  }

  String esc(String s) => s
      .replaceAll(r'\', r'\\')
      .replaceAll(';', r'\;')
      .replaceAll(',', r'\,')
      .replaceAll(RegExp(r'\r?\n'), r'\n');

  final location = [e.venueName, e.address].where((s) => s.isNotEmpty);
  return [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//Eventi Vicini//IT',
    'CALSCALE:GREGORIAN',
    'BEGIN:VEVENT',
    'UID:${e.id}@eventi-vicini',
    'DTSTAMP:${utc(now ?? DateTime.now())}',
    'DTSTART:${utc(e.startTime)}',
    'DTEND:${utc(e.endTime)}',
    'SUMMARY:${esc(e.title)}',
    if (e.shortDescription.isNotEmpty) 'DESCRIPTION:${esc(e.shortDescription)}',
    if (location.isNotEmpty) 'LOCATION:${esc(location.join(', '))}',
    if (e.ticketUrl.isNotEmpty) 'URL:${e.ticketUrl}',
    'END:VEVENT',
    'END:VCALENDAR',
    '',
  ].join('\r\n');
}

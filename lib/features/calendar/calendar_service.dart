import 'package:add_2_calendar/add_2_calendar.dart' as cal;
import 'package:flutter/foundation.dart';

import '../events/domain/event.dart';
import 'ics.dart';
import 'ics_download_stub.dart'
    if (dart.library.js_interop) 'ics_download_web.dart';

/// Su mobile apre il calendario di sistema, sul web scarica un file .ics.
Future<bool> addToCalendar(Event e) async {
  if (kIsWeb) {
    downloadIcs('${_slug(e.title)}.ics', buildIcs(e));
    return true;
  }
  return cal.Add2Calendar.addEvent2Cal(cal.Event(
    title: e.title,
    description: e.shortDescription,
    location: [e.venueName, e.address].where((s) => s.isNotEmpty).join(', '),
    startDate: e.startTime,
    endDate: e.endTime,
  ));
}

String _slug(String s) {
  final slug = s
      .toLowerCase()
      .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
      .replaceAll(RegExp(r'^-+|-+$'), '');
  return slug.isEmpty ? 'evento' : slug;
}

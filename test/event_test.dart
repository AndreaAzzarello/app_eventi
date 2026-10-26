import 'package:app_eventi/features/calendar/ics.dart';
import 'package:app_eventi/features/events/domain/event.dart';
import 'package:cloud_firestore/cloud_firestore.dart' show Timestamp;
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Event.fromMap', () {
    test('legge tutti i campi da millisecondi', () {
      final start = DateTime(2026, 11, 7, 21);
      final e = Event.fromMap('abc', {
        'title': 'Concerto',
        'shortDescription': 'Live',
        'category': 'music',
        'priceType': 'low',
        'startTime': start.millisecondsSinceEpoch,
        'endTime': start.add(const Duration(hours: 2)).millisecondsSinceEpoch,
        'venueName': 'Piazza Roma',
        'address': 'Piazza Roma, Modena',
        'lat': 44.646,
        'lng': 10,
        'imageUrl': 'https://x/y.jpg',
        'ticketUrl': '',
        'tags': ['live', 'kids'],
      });
      expect(e.id, 'abc');
      expect(e.title, 'Concerto');
      expect(e.startTime, start);
      expect(e.endTime, DateTime(2026, 11, 7, 23));
      expect(e.lng, 10.0);
      expect(e.tags, ['live', 'kids']);
      expect(e.isFree, isFalse);
      expect(e.isForKids, isTrue);
    });

    test('accetta Timestamp e stringhe ISO', () {
      final d = DateTime(2026, 5, 1, 10);
      final e = Event.fromMap('1', {
        'startTime': Timestamp.fromDate(d),
        'endTime': '2026-05-01T12:00:00',
        'lat': 1,
        'lng': 2,
      });
      expect(e.startTime, d);
      expect(e.endTime, DateTime(2026, 5, 1, 12));
    });

    test('valori mancanti usano i default', () {
      final e = Event.fromMap('1', {'startTime': 0});
      expect(e.title, '');
      expect(e.category, 'other');
      expect(e.priceType, 'free');
      expect(e.endTime, e.startTime);
      expect(e.lat, 0);
      expect(e.tags, isEmpty);
    });

    test('toMap → fromMap è reversibile', () {
      final a = Event.fromMap('1', {
        'title': 'X',
        'startTime': DateTime(2026, 1, 1).millisecondsSinceEpoch,
        'endTime': DateTime(2026, 1, 2).millisecondsSinceEpoch,
        'lat': 44.6,
        'lng': 10.9,
        'tags': ['a'],
      });
      expect(Event.fromMap('1', a.toMap()).toMap(), a.toMap());
    });
  });

  test('buildIcs produce un VEVENT in UTC con testo escapato', () {
    final e = Event.fromMap('ev1', {
      'title': 'Cena, vino; musica',
      'venueName': 'Cortile',
      'address': 'Via Emilia, Modena',
      'startTime': DateTime.utc(2026, 11, 7, 20).millisecondsSinceEpoch,
      'endTime': DateTime.utc(2026, 11, 7, 22).millisecondsSinceEpoch,
      'lat': 0,
      'lng': 0,
    });
    final ics = buildIcs(e, now: DateTime.utc(2026, 1, 1));
    expect(ics, contains('DTSTART:20261107T200000Z\r\n'));
    expect(ics, contains('DTEND:20261107T220000Z\r\n'));
    expect(ics, contains(r'SUMMARY:Cena\, vino\; musica'));
    expect(ics, contains(r'LOCATION:Cortile\, Via Emilia\, Modena'));
    expect(ics, contains('UID:ev1@eventi-vicini'));
    expect(ics.startsWith('BEGIN:VCALENDAR\r\n'), isTrue);
  });
}

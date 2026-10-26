import 'package:app_eventi/features/events/domain/event.dart';
import 'package:app_eventi/features/events/domain/event_filter.dart';
import 'package:flutter_test/flutter_test.dart';

// Mercoledì 28 ottobre 2026, ore 12.
final now = DateTime(2026, 10, 28, 12);
const lat = 44.6471, lng = 10.9252;

Event ev(
  String id, {
  required DateTime start,
  Duration length = const Duration(hours: 2),
  String category = 'music',
  String priceType = 'low',
  List<String> tags = const [],
  String title = 'Evento',
  double dLat = 0,
}) =>
    Event(
      id: id,
      title: title,
      shortDescription: '',
      category: category,
      priceType: priceType,
      startTime: start,
      endTime: start.add(length),
      venueName: 'Teatro Storchi',
      address: 'Largo Garibaldi, Modena',
      lat: lat + dLat,
      lng: lng,
      imageUrl: '',
      ticketUrl: '',
      tags: tags,
    );

List<String> ids(EventFilter f, List<Event> events, {DateTime? at}) => f
    .apply(events, now: at ?? now, originLat: lat, originLng: lng)
    .map((e) => e.id)
    .toList();

void main() {
  test('esclude gli eventi finiti e ordina per inizio', () {
    final events = [
      ev('later', start: now.add(const Duration(days: 2))),
      ev('past', start: now.subtract(const Duration(hours: 5))),
      ev('ongoing', start: now.subtract(const Duration(hours: 1))),
    ];
    expect(ids(const EventFilter(), events), ['ongoing', 'later']);
  });

  test('Oggi tiene solo gli eventi che toccano la giornata', () {
    final events = [
      ev('tonight', start: DateTime(2026, 10, 28, 21)),
      ev('tomorrow', start: DateTime(2026, 10, 29, 9)),
    ];
    expect(ids(const EventFilter(window: DateWindow.today), events),
        ['tonight']);
  });

  test('Weekend da mercoledì prende sabato e domenica successivi', () {
    final events = [
      ev('fri', start: DateTime(2026, 10, 30, 20)),
      ev('sat', start: DateTime(2026, 10, 31, 20)),
      ev('sun', start: DateTime(2026, 11, 1, 10)),
      ev('mon', start: DateTime(2026, 11, 2, 10)),
    ];
    expect(ids(const EventFilter(window: DateWindow.weekend), events),
        ['sat', 'sun']);
  });

  test('Weekend di domenica include ancora la domenica', () {
    final sunday = DateTime(2026, 11, 1, 9);
    final events = [
      ev('sun', start: DateTime(2026, 11, 1, 18)),
      ev('nextSat', start: DateTime(2026, 11, 7, 18)),
    ];
    expect(
        ids(const EventFilter(window: DateWindow.weekend), events, at: sunday),
        ['sun']);
  });

  test('Gratis, Bambini e categoria', () {
    final start = now.add(const Duration(hours: 3));
    final events = [
      ev('free', start: start, priceType: 'free'),
      ev('kidsCat', start: start, category: 'kids'),
      ev('familyTag', start: start, tags: ['family'], category: 'food'),
    ];
    expect(ids(const EventFilter(onlyFree: true), events), ['free']);
    expect(ids(const EventFilter(onlyKids: true), events),
        ['kidsCat', 'familyTag']);
    expect(ids(const EventFilter(category: 'food'), events), ['familyTag']);
  });

  test('ricerca testuale senza distinzione maiuscole', () {
    final start = now.add(const Duration(hours: 3));
    final events = [
      ev('a', start: start, title: 'Mercatino di Natale'),
      ev('b', start: start, title: 'Jazz night'),
    ];
    expect(ids(const EventFilter(query: '  NATALE '), events), ['a']);
    // Cerca anche in luogo e indirizzo.
    expect(ids(const EventFilter(query: 'storchi'), events), ['a', 'b']);
  });

  test('raggio in km', () {
    final start = now.add(const Duration(hours: 3));
    // 0.1° di latitudine ≈ 11 km
    final events = [
      ev('near', start: start),
      ev('far', start: start, dLat: 0.1),
    ];
    expect(ids(const EventFilter(radiusKm: 5), events), ['near']);
    expect(ids(const EventFilter(radiusKm: 20), events), ['near', 'far']);
  });

  test('copyWith può azzerare la categoria', () {
    const f = EventFilter(category: 'music');
    expect(f.copyWith(category: () => null).category, isNull);
    expect(f.copyWith(onlyFree: true).category, 'music');
  });
}

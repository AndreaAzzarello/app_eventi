import 'package:app_eventi/features/events/application/providers.dart';
import 'package:app_eventi/features/events/domain/event.dart';
import 'package:app_eventi/features/location/location_service.dart';
import 'package:app_eventi/main.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:shared_preferences/shared_preferences.dart';

Event _event(String id, String title, {String category = 'music'}) {
  final start = DateTime.now().add(const Duration(hours: 2));
  return Event(
    id: id,
    title: title,
    shortDescription: '',
    category: category,
    priceType: 'free',
    startTime: start,
    endTime: start.add(const Duration(hours: 2)),
    venueName: 'Piazza Grande',
    address: 'Piazza Grande, Modena',
    lat: 44.6471,
    lng: 10.9252,
    imageUrl: '',
    ticketUrl: '',
    tags: const [],
  );
}

Future<void> _pumpApp(WidgetTester tester, Stream<List<Event>> events) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        eventsProvider.overrideWith((ref) => events),
        userLocationProvider.overrideWith(
          (ref) async => const UserLocation(modenaCenter, isFallback: true),
        ),
      ],
      child: const EventiApp(),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  setUpAll(() => initializeDateFormatting('it_IT'));
  setUp(() => SharedPreferences.setMockInitialValues({}));

  testWidgets('mostra gli eventi e filtra per categoria', (tester) async {
    await _pumpApp(
      tester,
      Stream.value([
        _event('1', 'Concerto in piazza'),
        _event('2', 'Sagra del quartiere', category: 'food'),
      ]),
    );

    expect(find.text('Eventi Vicini'), findsOneWidget);
    expect(find.text('Concerto in piazza'), findsOneWidget);
    expect(find.text('Sagra del quartiere'), findsOneWidget);

    await tester.tap(find.widgetWithText(ChoiceChip, 'Cibo'));
    await tester.pumpAndSettle();
    expect(find.text('Concerto in piazza'), findsNothing);
    expect(find.text('Sagra del quartiere'), findsOneWidget);
  });

  testWidgets('lista vuota e preferiti vuoti', (tester) async {
    await _pumpApp(tester, Stream.value(const []));
    expect(find.text('Nessun evento qui'), findsOneWidget);

    await tester.tap(find.text('Preferiti'));
    await tester.pumpAndSettle();
    expect(find.text('Ancora nessun preferito'), findsOneWidget);
  });

  testWidgets('nessun overflow su schermo stretto', (tester) async {
    tester.view.physicalSize = const Size(360, 740);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await _pumpApp(
      tester,
      Stream.value([
        _event('1', 'Un titolo molto lungo per un evento in piazza a Modena'),
      ]),
    );
    expect(tester.takeException(), isNull);
    expect(find.text('Lista'), findsOneWidget);
  });

  testWidgets('errore di caricamento', (tester) async {
    await _pumpApp(tester, Stream.error('Firebase non configurato'));
    expect(find.text('Impossibile caricare gli eventi'), findsOneWidget);
    expect(find.text('Riprova'), findsOneWidget);
  });
}

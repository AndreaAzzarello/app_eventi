import 'package:app_eventi/features/admin/admin_repository.dart';
import 'package:app_eventi/features/auth/auth.dart';
import 'package:app_eventi/features/events/domain/event.dart';
import 'package:app_eventi/main.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';

class _FakeRepo extends AdminRepository {
  final saved = <Event>[];
  final deleted = <String>[];
  @override
  Future<String> save(Event e) async {
    saved.add(e);
    return e.id.isEmpty ? 'new' : e.id;
  }

  @override
  Future<void> delete(String id) async => deleted.add(id);
}

Event _event(String id, String title, {int days = 1, String source = 'manual'}) {
  final start = DateTime.now().add(Duration(days: days));
  return Event(
    id: id,
    title: title,
    shortDescription: 'Descrizione',
    category: 'music',
    priceType: 'free',
    startTime: start,
    endTime: start.add(const Duration(hours: 2)),
    venueName: 'Piazza Grande',
    address: 'Piazza Grande, Modena',
    lat: 44.6471,
    lng: 10.9252,
    imageUrl: '',
    ticketUrl: '',
    tags: const ['kids'],
    source: source,
  );
}

Future<_FakeRepo> _pump(WidgetTester tester, AuthState auth,
    {String location = '/admin', List<Event> events = const []}) async {
  tester.view.physicalSize = const Size(800, 2400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  final repo = _FakeRepo();
  await tester.pumpWidget(ProviderScope(
    overrides: [
      authStateProvider.overrideWith((ref) => Stream.value(auth)),
      allEventsProvider.overrideWith((ref) => Stream.value(events)),
      adminRepositoryProvider.overrideWithValue(repo),
    ],
    child: EventiApp(initialLocation: location),
  ));
  await tester.pumpAndSettle();
  return repo;
}

const _admin = AuthState(email: adminEmail, isAdmin: true);

void main() {
  setUpAll(() => initializeDateFormatting('it_IT'));

  testWidgets('senza login chiede di accedere', (tester) async {
    await _pump(tester, const AuthState());
    expect(find.text('Area riservata'), findsOneWidget);
    expect(find.text('Accedi con Google'), findsOneWidget);
  });

  testWidgets('utente non admin non entra', (tester) async {
    await _pump(tester, const AuthState(email: 'altro@example.com'));
    expect(find.text('Account non autorizzato'), findsOneWidget);
    expect(find.text('Nuovo evento'), findsNothing);
  });

  testWidgets('lista con eventi passati, ricerca ed eliminazione', (tester) async {
    final repo = await _pump(tester, _admin, events: [
      _event('1', 'Concerto in piazza'),
      _event('2', 'Mostra conclusa', days: -10, source: 'scraper'),
    ]);
    expect(find.text('Concerto in piazza'), findsOneWidget);
    expect(find.text('Mostra conclusa'), findsOneWidget);
    expect(find.textContaining('Passato · Import'), findsOneWidget);

    await tester.enterText(find.byType(TextField), 'mostra');
    await tester.pumpAndSettle();
    expect(find.text('Concerto in piazza'), findsNothing);

    await tester.tap(find.byTooltip('Elimina'));
    await tester.pumpAndSettle();
    expect(find.text('Eliminare l\'evento?'), findsOneWidget);
    await tester.tap(find.widgetWithText(FilledButton, 'Elimina'));
    await tester.pumpAndSettle();
    expect(repo.deleted, ['2']);
    expect(find.text('Eliminato "Mostra conclusa"'), findsOneWidget);
  });

  testWidgets('il form nuovo evento valida i campi obbligatori', (tester) async {
    final repo = await _pump(tester, _admin);
    await tester.tap(find.text('Nuovo evento'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Salva evento'));
    await tester.pumpAndSettle();
    expect(find.text('Campo obbligatorio'), findsNWidgets(4));
    expect(find.textContaining('Trova coordinate'), findsWidgets);
    expect(repo.saved, isEmpty);
  });

  testWidgets('modifica di un evento importato lo rende manuale', (tester) async {
    final repo = await _pump(tester, _admin,
        location: '/admin/events/7',
        events: [_event('7', 'Sagra', source: 'scraper')]);
    expect(find.text('Evento importato automaticamente'), findsOneWidget);
    await tester.enterText(find.widgetWithText(TextFormField, 'Sagra'), 'Sagra d\'autunno');
    await tester.tap(find.text('Salva evento'));
    await tester.pumpAndSettle();
    expect(repo.saved.single.id, '7');
    expect(repo.saved.single.title, 'Sagra d\'autunno');
    expect(repo.saved.single.source, 'manual');
    expect(repo.saved.single.tags, ['kids']);
    expect(find.text('Evento non trovato'), findsNothing);
  });
}

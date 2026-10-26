import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_web_plugins/url_strategy.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:intl/intl.dart';

import 'app/theme.dart';
import 'firebase_options.dart';
import 'pages/admin/admin_events_page.dart';
import 'pages/admin/admin_gate.dart';
import 'pages/admin/event_form_page.dart';
import 'pages/events_list_map_page.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // URL senza "#" sul web: firebase.json riscrive già tutto su index.html.
  usePathUrlStrategy();
  Intl.defaultLocale = 'it_IT';
  await initializeDateFormatting('it_IT');
  try {
    await Firebase.initializeApp(
        options: DefaultFirebaseOptions.currentPlatform);
  } catch (e) {
    // L'app parte comunque: la lista mostrerà lo stato di errore.
    debugPrint('Firebase non inizializzato: $e');
  }
  runApp(const ProviderScope(child: EventiApp()));
}

GoRouter buildRouter({String initialLocation = '/'}) => GoRouter(
      initialLocation: initialLocation,
      routes: [
        GoRoute(path: '/', builder: (_, _) => const EventsListMapPage()),
        // /admin non compare nella navigazione: ci si arriva solo dall'URL.
        GoRoute(
          path: '/admin',
          builder: (_, _) => const AdminGate(child: AdminEventsPage()),
          routes: [
            GoRoute(
              path: 'events/new',
              builder: (_, _) => const AdminGate(child: EventFormPage()),
            ),
            GoRoute(
              path: 'events/:id',
              builder: (_, s) => AdminGate(
                  child: EventFormPage(eventId: s.pathParameters['id'])),
            ),
          ],
        ),
      ],
    );

class EventiApp extends StatefulWidget {
  final String initialLocation;
  const EventiApp({super.key, this.initialLocation = '/'});

  @override
  State<EventiApp> createState() => _EventiAppState();
}

class _EventiAppState extends State<EventiApp> {
  late final _router = buildRouter(initialLocation: widget.initialLocation);

  @override
  void dispose() {
    _router.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Eventi Vicini',
      debugShowCheckedModeBanner: false,
      theme: buildTheme(Brightness.light),
      darkTheme: buildTheme(Brightness.dark),
      locale: const Locale('it', 'IT'),
      supportedLocales: const [Locale('it', 'IT')],
      localizationsDelegates: GlobalMaterialLocalizations.delegates,
      routerConfig: _router,
    );
  }
}

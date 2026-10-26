import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../common/utils/geo.dart';
import '../features/events/application/providers.dart';
import '../features/events/data/event_service.dart';
import '../features/events/domain/event.dart';
import '../features/location/location_service.dart';
import '../widgets/event_card.dart';
import '../widgets/events_map.dart';
import '../widgets/filter_bar.dart';
import '../widgets/state_views.dart';
import 'event_details_page.dart';

/// Sotto questa larghezza: tab separati; sopra: lista e mappa affiancate.
const _wideBreakpoint = 900.0;

class EventsListMapPage extends ConsumerStatefulWidget {
  const EventsListMapPage({super.key});

  @override
  ConsumerState<EventsListMapPage> createState() => _EventsListMapPageState();
}

enum _Section { list, map, favorites }

class _EventsListMapPageState extends ConsumerState<EventsListMapPage> {
  _Section _section = _Section.list;

  void _openDetails(Event e) => Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => EventDetailsPage(event: e)));

  Future<void> _seedDemo() async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      await seedSampleEvents();
      messenger.showSnackBar(
          const SnackBar(content: Text('10 eventi demo caricati')));
    } catch (e) {
      messenger.showSnackBar(SnackBar(
          content: Text('Seed fallito (regole Firestore o emulatore?): $e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final wide = MediaQuery.sizeOf(context).width >= _wideBreakpoint;
    // In layout largo "Mappa" è già accanto alla lista.
    final section =
        wide && _section == _Section.map ? _Section.list : _section;
    final location = ref.watch(userLocationProvider).value;

    final appBar = AppBar(
      title: const Text('Eventi Vicini'),
      actions: [
        if (location?.isFallback ?? false)
          const Tooltip(
            message: 'Posizione non disponibile: uso Modena centro',
            child: Padding(
              padding: EdgeInsets.symmetric(horizontal: 8),
              child: Icon(Icons.location_disabled_rounded),
            ),
          ),
        if (kDebugMode)
          IconButton(
            tooltip: 'Carica eventi demo',
            onPressed: _seedDemo,
            icon: const Icon(Icons.auto_awesome_rounded),
          ),
        const SizedBox(width: 8),
      ],
    );

    final Widget body = switch (section) {
      _Section.favorites => _FavoritesView(onTap: _openDetails),
      _Section.map => Column(children: [
          const FilterBar(),
          Expanded(child: _MapView(onTap: _openDetails)),
        ]),
      _Section.list when wide => Row(children: [
          SizedBox(
            width: 440,
            child: Column(children: [
              const FilterBar(),
              Expanded(child: _ListView(onTap: _openDetails, onSeed: _seedDemo)),
            ]),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(0, 0, 16, 16),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(24),
                child: _MapView(onTap: _openDetails),
              ),
            ),
          ),
        ]),
      _Section.list => Column(children: [
          const FilterBar(),
          Expanded(child: _ListView(onTap: _openDetails, onSeed: _seedDemo)),
        ]),
    };

    if (wide) {
      return Scaffold(
        appBar: appBar,
        body: Row(children: [
          NavigationRail(
            selectedIndex: section == _Section.favorites ? 1 : 0,
            labelType: NavigationRailLabelType.all,
            onDestinationSelected: (i) => setState(
                () => _section = i == 1 ? _Section.favorites : _Section.list),
            destinations: const [
              NavigationRailDestination(
                  icon: Icon(Icons.explore_outlined),
                  selectedIcon: Icon(Icons.explore_rounded),
                  label: Text('Esplora')),
              NavigationRailDestination(
                  icon: Icon(Icons.favorite_border_rounded),
                  selectedIcon: Icon(Icons.favorite_rounded),
                  label: Text('Preferiti')),
            ],
          ),
          Expanded(child: body),
        ]),
      );
    }

    return Scaffold(
      appBar: appBar,
      body: body,
      bottomNavigationBar: NavigationBar(
        selectedIndex: section.index,
        onDestinationSelected: (i) =>
            setState(() => _section = _Section.values[i]),
        destinations: const [
          NavigationDestination(
              icon: Icon(Icons.view_agenda_outlined),
              selectedIcon: Icon(Icons.view_agenda_rounded),
              label: 'Lista'),
          NavigationDestination(
              icon: Icon(Icons.map_outlined),
              selectedIcon: Icon(Icons.map_rounded),
              label: 'Mappa'),
          NavigationDestination(
              icon: Icon(Icons.favorite_border_rounded),
              selectedIcon: Icon(Icons.favorite_rounded),
              label: 'Preferiti'),
        ],
      ),
    );
  }
}

/// Gestisce caricamento ed errore comuni a lista, mappa e preferiti.
Widget _async(
  AsyncValue<List<Event>> value,
  WidgetRef ref,
  Widget Function(List<Event>) data,
) =>
    value.when(
      loading: () => const LoadingView(),
      error: (e, _) => MessageView(
        icon: Icons.cloud_off_rounded,
        title: 'Impossibile caricare gli eventi',
        message: e is StateError ? e.message : '$e',
        action: FilledButton.tonal(
          onPressed: () => ref.invalidate(eventsProvider),
          child: const Text('Riprova'),
        ),
      ),
      data: data,
    );

class _ListView extends ConsumerWidget {
  final ValueChanged<Event> onTap;
  final VoidCallback onSeed;
  const _ListView({required this.onTap, required this.onSeed});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final origin =
        ref.watch(userLocationProvider).value?.position ?? modenaCenter;
    return _async(ref.watch(filteredEventsProvider), ref, (events) {
      if (events.isEmpty) {
        return MessageView(
          icon: Icons.event_busy_rounded,
          title: 'Nessun evento qui',
          message: 'Prova ad allargare il raggio o a togliere qualche filtro.',
          action: kDebugMode
              ? OutlinedButton.icon(
                  onPressed: onSeed,
                  icon: const Icon(Icons.auto_awesome_rounded),
                  label: const Text('Carica eventi demo'),
                )
              : null,
        );
      }
      return _EventList(
        events: events,
        distanceFrom: (e) => haversineKm(
            origin.latitude, origin.longitude, e.lat, e.lng),
        onTap: onTap,
      );
    });
  }
}

class _MapView extends ConsumerWidget {
  final ValueChanged<Event> onTap;
  const _MapView({required this.onTap});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final location = ref.watch(userLocationProvider).value;
    // Niente stato di errore qui: la mappa resta usabile, l'errore lo mostra la lista.
    return EventsMap(
      events: ref.watch(filteredEventsProvider).value ?? const [],
      center: location?.position ?? modenaCenter,
      showUser: !(location?.isFallback ?? true),
      onEventTap: onTap,
    );
  }
}

class _FavoritesView extends ConsumerWidget {
  final ValueChanged<Event> onTap;
  const _FavoritesView({required this.onTap});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return _async(ref.watch(favoriteEventsProvider), ref, (events) {
      if (events.isEmpty) {
        return const MessageView(
          icon: Icons.favorite_border_rounded,
          title: 'Ancora nessun preferito',
          message: 'Tocca il cuore su un evento per ritrovarlo qui.',
        );
      }
      return _EventList(events: events, onTap: onTap);
    });
  }
}

class _EventList extends ConsumerWidget {
  final List<Event> events;
  final double Function(Event)? distanceFrom;
  final ValueChanged<Event> onTap;
  const _EventList(
      {required this.events, required this.onTap, this.distanceFrom});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final favs = ref.watch(favoritesProvider).value ?? const <String>{};
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 720),
        child: ListView.separated(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
          itemCount: events.length,
          separatorBuilder: (_, _) => const SizedBox(height: 12),
          itemBuilder: (_, i) {
            final e = events[i];
            return EventCard(
              event: e,
              isFavorite: favs.contains(e.id),
              distanceKm: distanceFrom?.call(e),
              onTap: () => onTap(e),
              onToggleFavorite: () =>
                  ref.read(favoritesProvider.notifier).toggle(e.id),
            );
          },
        ),
      ),
    );
  }
}

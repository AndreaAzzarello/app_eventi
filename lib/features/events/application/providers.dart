import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../favorites/favorites_store.dart';
import '../../location/location_service.dart';
import '../data/event_service.dart';
import '../domain/event.dart';
import '../domain/event_filter.dart';

final eventsProvider =
    StreamProvider<List<Event>>((ref) => EventService().watchAll());

final userLocationProvider =
    FutureProvider<UserLocation>((ref) => LocationService().current());

final eventFilterProvider =
    NotifierProvider<EventFilterNotifier, EventFilter>(EventFilterNotifier.new);

class EventFilterNotifier extends Notifier<EventFilter> {
  @override
  EventFilter build() => const EventFilter();

  /// Oggi e Weekend si escludono: riselezionare lo stesso chip lo spegne.
  void toggleWindow(DateWindow w) => state =
      state.copyWith(window: state.window == w ? DateWindow.any : w);
  void toggleFree() => state = state.copyWith(onlyFree: !state.onlyFree);
  void toggleKids() => state = state.copyWith(onlyKids: !state.onlyKids);
  void setCategory(String? c) => state = state.copyWith(category: () => c);
  void setQuery(String q) => state = state.copyWith(query: q);
  void setRadius(double km) => state = state.copyWith(radiusKm: km);
}

/// Eventi filtrati attorno all'utente. Finché la posizione non arriva usa Modena.
final filteredEventsProvider = Provider<AsyncValue<List<Event>>>((ref) {
  final filter = ref.watch(eventFilterProvider);
  final origin = ref.watch(userLocationProvider).value?.position ?? modenaCenter;
  return ref.watch(eventsProvider).whenData((list) => filter.apply(
        list,
        now: DateTime.now(),
        originLat: origin.latitude,
        originLng: origin.longitude,
      ));
});

final favoritesProvider =
    AsyncNotifierProvider<FavoritesNotifier, Set<String>>(FavoritesNotifier.new);

class FavoritesNotifier extends AsyncNotifier<Set<String>> {
  final _store = FavoritesStore();

  @override
  Future<Set<String>> build() => _store.all();

  Future<void> toggle(String id) async {
    final cur = {...?state.value};
    cur.contains(id) ? cur.remove(id) : cur.add(id);
    state = AsyncData(cur);
    await _store.toggle(id);
  }
}

final favoriteEventsProvider = Provider<AsyncValue<List<Event>>>((ref) {
  final ids = ref.watch(favoritesProvider).value ?? const <String>{};
  return ref.watch(eventsProvider).whenData((list) =>
      list.where((e) => ids.contains(e.id)).toList()
        ..sort((a, b) => a.startTime.compareTo(b.startTime)));
});

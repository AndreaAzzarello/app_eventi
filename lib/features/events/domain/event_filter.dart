import '../../../common/utils/geo.dart';
import 'event.dart';

enum DateWindow { any, today, weekend }

/// Stato dei filtri della home. Immutabile: il notifier ne crea copie.
class EventFilter {
  final DateWindow window;
  final bool onlyFree;
  final bool onlyKids;
  final String? category;
  final String query;
  final double radiusKm;

  const EventFilter({
    this.window = DateWindow.any,
    this.onlyFree = false,
    this.onlyKids = false,
    this.category,
    this.query = '',
    this.radiusKm = 25,
  });

  EventFilter copyWith({
    DateWindow? window,
    bool? onlyFree,
    bool? onlyKids,
    String? Function()? category,
    String? query,
    double? radiusKm,
  }) =>
      EventFilter(
        window: window ?? this.window,
        onlyFree: onlyFree ?? this.onlyFree,
        onlyKids: onlyKids ?? this.onlyKids,
        category: category != null ? category() : this.category,
        query: query ?? this.query,
        radiusKm: radiusKm ?? this.radiusKm,
      );

  /// Eventi non ancora finiti che passano tutti i filtri, ordinati per inizio.
  List<Event> apply(
    Iterable<Event> events, {
    required DateTime now,
    required double originLat,
    required double originLng,
  }) {
    final range = _range(now);
    final q = query.trim().toLowerCase();
    return events.where((e) {
      if (e.endTime.isBefore(now)) return false;
      if (range != null &&
          !(e.startTime.isBefore(range.$2) && e.endTime.isAfter(range.$1))) {
        return false;
      }
      if (onlyFree && !e.isFree) return false;
      if (onlyKids && !e.isForKids) return false;
      if (category != null && e.category != category) return false;
      if (q.isNotEmpty &&
          !'${e.title} ${e.shortDescription} ${e.venueName} ${e.address}'
              .toLowerCase()
              .contains(q)) {
        return false;
      }
      return haversineKm(originLat, originLng, e.lat, e.lng) <= radiusKm;
    }).toList()
      ..sort((a, b) => a.startTime.compareTo(b.startTime));
  }

  (DateTime, DateTime)? _range(DateTime now) {
    final today = DateTime(now.year, now.month, now.day);
    switch (window) {
      case DateWindow.any:
        return null;
      case DateWindow.today:
        return (today, DateTime(now.year, now.month, now.day + 1));
      case DateWindow.weekend:
        // Di domenica il weekend in corso è iniziato ieri.
        final toSat = now.weekday == DateTime.sunday
            ? -1
            : DateTime.saturday - now.weekday;
        final sat = DateTime(now.year, now.month, now.day + toSat);
        return (sat, DateTime(sat.year, sat.month, sat.day + 2));
    }
  }
}

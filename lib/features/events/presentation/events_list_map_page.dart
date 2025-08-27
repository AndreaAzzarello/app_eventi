import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:geolocator/geolocator.dart' as geo;
import 'package:mapbox_maps_flutter/mapbox_maps_flutter.dart' as mapbox;
import '../../events/data/event_service.dart';
import '../../events/domain/event.dart';
import '../../favorites/favorites_store.dart';

const _mapboxToken = 'pk.eyJ1IjoiYW5kcmVhenphcmVsbG8iLCJhIjoiY21lc295MW1rMDQ5NTJscXY0bHdqN2hvZSJ9.5rX0woMmxCYRDRxtH0RYfw';

class EventsListMapPage extends StatefulWidget {
  const EventsListMapPage({super.key});
  @override
  State<EventsListMapPage> createState() => _EventsListMapPageState();
}

class _EventsListMapPageState extends State<EventsListMapPage> with TickerProviderStateMixin {
  late final TabController _tab;
  final _svc = EventService();
  final _fav = FavoritesStore();

  List<Event> _events = [];
  bool _loading = true;

  bool _freeOnly = false;
  bool _todayOnly = false;
  bool _weekendOnly = false;
  bool _kidsOnly = false;

  mapbox.MapboxMap? _map;
  mapbox.PointAnnotationManager? _pam;
  geo.Position? _userPos;

  @override
  void initState() {
    super.initState();
    _tab = TabController(length: 2, vsync: this);
    _load();
  }

  Future<void> _load() async {
    await _ensurePermissions();
    try {
      _userPos = await geo.Geolocator.getCurrentPosition();
    } catch (_) {
      _userPos = null;
    }
    var fetchNearby = _svc.fetchNearby(
      userLat: _userPos?.latitude ?? 41.9028, // fallback to Rome latitude
      userLng: _userPos?.longitude ?? 12.4964, // fallback to Rome longitude
    );
    final data = await newMethod(fetchNearby);
    setState(() {
      _events = data;
      _loading = false;
    });
    await _refreshMarkers();
  }

  Future<List<Event>> newMethod(Future<List<Event>> fetchNearby) => fetchNearby;

  Future<void> _ensurePermissions() async {
    final enabled = await geo.Geolocator.isLocationServiceEnabled();
    if (!enabled && mounted) _snack('Attiva il GPS');

    var p = await geo.Geolocator.checkPermission();
    if (p == geo.LocationPermission.denied) {
      p = await geo.Geolocator.requestPermission();
    }
    if (p == geo.LocationPermission.denied || p == geo.LocationPermission.deniedForever) {
      if (mounted) _snack('Permessi posizione negati. Uso fallback.');
    }
  }

  List<Event> _applyFilters(List<Event> all) {
    // Implementa qui i filtri reali in base alla struttura di Event.
    return all;
  }

  Future<void> _refreshMarkers() async {
    if (_map == null || _pam == null) return;
    _applyFilters(_events);
    try {
      await _pam!.deleteAll();
    } catch (_) {}

    // Aggiungi un marker per la posizione utente (se presente)
    if (_userPos != null) {
      final userPoint = mapbox.Point(coordinates: mapbox.Position(_userPos!.longitude, _userPos!.latitude));
      await _pam!.create(mapbox.PointAnnotationOptions(
        geometry: userPoint,
        textField: 'Sei qui',
        textOffset: [0.0, -2.0],
        iconImage: 'marker-15',
      ));
    }

    // TODO: aggiungere marker per ogni evento se Event espone lat/lng
    // Esempio (se Event ha .latitude e .longitude):
    // for (final e in filtered) {
    //   final pt = mapbox.Point(coordinates: mapbox.Position(e.longitude, e.latitude));
    //   await _pam!.create(mapbox.PointAnnotationOptions(
    //     geometry: pt.toJson(),
    //     textField: e.title ?? '',
    //     iconImage: 'marker-15',
    //   ));
    // }
  }

  @override
  Widget build(BuildContext context) {
    final df = DateFormat('dd-MMM-yyyy HH:mm');
    final filtered = _applyFilters(_events);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Eventi'),
        bottom: TabBar(
          controller: _tab,
          tabs: const [
            Tab(text: 'Lista'),
            Tab(text: 'Mappa'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tab,
        children: [
          _loading
              ? const Center(child: CircularProgressIndicator())
              : ListView.builder(
                  itemCount: filtered.length,
                  itemBuilder: (context, i) {
                    final e = filtered[i];
                    return ListTile(
                      title: Text(e.toString()), // sostituire con e.title se esiste
                      subtitle: Text(df.format(e.lat as DateTime)),
                      onTap: () => _showEventSheet(e),
                      trailing: IconButton(
                        icon: const Icon(Icons.favorite_border),
                        onPressed: () {
                          _fav.toggle(e.id); // Pass the event's ID or unique string identifier
                          setState(() {});
                        },
                      ),
                    );
                  },
                ),
          // Map tab
          mapbox.MapWidget(
            key: const ValueKey('eventsMap'),
            styleUri: mapbox.MapboxStyles.MAPBOX_STREETS,
            onMapCreated: (mapbox.MapboxMap controller) async {
              _map = controller;
              _pam = await _map!.annotations.createPointAnnotationManager();
              await _refreshMarkers();
            },
            cameraOptions: _userPos != null
                ? mapbox.CameraOptions(center: mapbox.Point(coordinates: mapbox.Position(_userPos!.longitude, _userPos!.latitude)), zoom: 12)
                : mapbox.CameraOptions(center: mapbox.Point(coordinates: mapbox.Position(12.4964, 41.9028)), zoom: 12),
          ),
        ],
      ),
      bottomNavigationBar: SizedBox(height: 56, child: _filtersBar()),
    );
  }

  Widget _filtersBar() {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 10),
      child: Row(
        children: [
          FilterChip(
            label: const Text('Solo gratuiti'),
            selected: _freeOnly,
            onSelected: (v) => setState(() => _freeOnly = v),
          ),
          const SizedBox(width: 8),
          FilterChip(
            label: const Text('Oggi'),
            selected: _todayOnly,
            onSelected: (v) => setState(() => _todayOnly = v),
          ),
          const SizedBox(width: 8),
          FilterChip(
            label: const Text('Weekend'),
            selected: _weekendOnly,
            onSelected: (v) => setState(() => _weekendOnly = v),
          ),
          const SizedBox(width: 8),
          FilterChip(
            label: const Text('Kids'),
            selected: _kidsOnly,
            onSelected: (v) => setState(() => _kidsOnly = v),
          ),
        ],
      ),
    );
  }

  void _showEventSheet(Event e) {
    showModalBottomSheet(
      context: context,
      builder: (_) {
        return Padding(
          padding: const EdgeInsets.all(16),
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(e.toString(), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                Text('Dettagli...'), // sostituire con campi reali di Event
                const SizedBox(height: 8),
                ElevatedButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Chiudi'),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  void _snack(String m) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));
  }
}

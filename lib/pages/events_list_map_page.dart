import 'dart:math';
import 'package:flutter/material.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:geocoding/geocoding.dart';
import 'package:mapbox_maps_flutter/mapbox_maps_flutter.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/event.dart';
import '../services/firestore_service.dart';
import '../services/location_service.dart';
import '../widgets/event_card.dart';
import '../widgets/filter_bar.dart';
import 'event_details_page.dart';

class EventsListMapPage extends StatefulWidget {
  const EventsListMapPage({super.key});

  @override
  State<EventsListMapPage> createState() => _EventsListMapPageState();
}

class _EventsListMapPageState extends State<EventsListMapPage>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs;
  MapboxMap? _map;
  PointAnnotationManager? _pointManager;

  // Filtri UI
  bool onlyFree = false;
  bool onlyToday = false;
  bool onlyWeekend = false;
  bool onlyKids = false;

  // Ricerca
  final _searchCtl = TextEditingController();

  // Centro mappa e raggio filtro
  double? _centerLat;
  double? _centerLng;
  double _radiusKm = 25;

  // Dati
  List<EventModel> _events = [];
  Set<String> _favorites = {};

  // Gestione dello stream Firestore per evitare più listener
  Stream<List<EventModel>>? _activeStream;
  Stream<List<EventModel>> _buildStream() {
    final range = _timeRange();
    final price = onlyFree ? PriceTier.free : null;
    final kids = onlyKids ? true : null;

    return FirestoreService.instance.eventsStream(
      from: range.start,
      to: range.end,
      priceTier: price,
      kidsOnly: kids,
    );
  }

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 2, vsync: this);
    _init();
  }

  @override
  void dispose() {
    _tabs.dispose();
    _searchCtl.dispose();
    super.dispose();
  }

  Future<void> _init() async {
    // Token Mapbox da --dart-define (se lo usi così)
    final token = const String.fromEnvironment('MAPBOX_ACCESS_TOKEN');
    if (token.isNotEmpty) {
      MapboxOptions.setAccessToken(token);
    }

    final prefs = await SharedPreferences.getInstance();
    _favorites = prefs.getStringList('favorites')?.toSet() ?? {};

    final pos = await LocationService.getCurrentPosition();
    if (pos != null) {
      _centerLat = pos.latitude;
      _centerLng = pos.longitude;
    } else {
      // fallback
      _centerLat = 45.4384; // Verona
      _centerLng = 10.9916;
    }

    // Carica eventi iniziali
    _subscribeAndLoad();
    setState(() {});
  }

  void _subscribeAndLoad() {
    _activeStream ??= _buildStream();
    _activeStream!.listen((list) {
      List<EventModel> filtered = list;
      if (_centerLat != null && _centerLng != null) {
        filtered = list
            .where((e) =>
                _haversineKm(_centerLat!, _centerLng!, e.lat, e.lng) <=
                _radiusKm)
            .toList();
      }
      setState(() {
        _events = filtered;
      });
      _refreshAnnotations();
    });
  }

  DateTimeRange _timeRange() {
    final now = DateTime.now();
    if (onlyToday) {
      final start = DateTime(now.year, now.month, now.day);
      final end = start
          .add(const Duration(days: 1))
          .subtract(const Duration(seconds: 1));
      return DateTimeRange(start: start, end: end);
    }
    if (onlyWeekend) {
      final daysToSat = (DateTime.saturday - now.weekday) % 7;
      final sat = DateTime(now.year, now.month, now.day)
          .add(Duration(days: daysToSat));
      final sunEnd = sat
          .add(const Duration(days: 2))
          .subtract(const Duration(seconds: 1));
      return DateTimeRange(start: sat, end: sunEnd);
    }
    // Default: prossimi 14 giorni
    return DateTimeRange(start: now, end: now.add(const Duration(days: 14)));
  }

  double _haversineKm(
      double lat1, double lon1, double lat2, double lon2) {
    const R = 6371.0;
    final dLat = _deg2rad(lat2 - lat1);
    final dLon = _deg2rad(lon2 - lon1);
    final a = sin(dLat / 2) * sin(dLat / 2) +
        cos(_deg2rad(lat1)) *
            cos(_deg2rad(lat2)) *
            sin(dLon / 2) *
            sin(dLon / 2);
    final c = 2 * atan2(sqrt(a), sqrt(1 - a));
    return R * c;
  }

  double _deg2rad(double deg) => deg * (pi / 180.0);

  // ===== MAPPA =====
  void _onMapCreated(MapboxMap mapboxMap) async {
    _map = mapboxMap;
    _pointManager =
        await _map!.annotations.createPointAnnotationManager();
    _refreshAnnotations();

    // Posiziona la camera sul centro
    if (_centerLat != null && _centerLng != null) {
      await _map!.setCamera(
        CameraOptions(
          center: Point(
            coordinates: Position(_centerLng!, _centerLat!),
          ).toJson(),
          zoom: 11,
        ),
      );
    }
  }

  Future<void> _refreshAnnotations() async {
    if (_pointManager == null) return;
    await _pointManager!.deleteAll();

    for (final e in _events) {
      await _pointManager!.create(
        PointAnnotationOptions(
          geometry: Point(
            coordinates: Position(e.lng, e.lat),
          ).toJson(),
          iconSize: 1.0,
          textField: e.title,
          textOffset: [0, 1.6],
        ),
      );
    }
  }

  Future<void> _searchAddress(String query) async {
    if (query.trim().isEmpty) return;
    try {
      final results = await locationFromAddress(query);
      if (results.isNotEmpty) {
        final loc = results.first;
        _centerLat = loc.latitude;
        _centerLng = loc.longitude;

        if (_map != null) {
          await _map!.flyTo(
            CameraOptions(
              center: Point(
                coordinates: Position(_centerLng!, _centerLat!),
              ).toJson(),
              zoom: 11,
            ),
          );
        }
        _activeStream = null; // ricrea stream (per sicurezza)
        _subscribeAndLoad();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Indirizzo non trovato: $query')),
        );
      }
    }
  }

  Future<void> _seedDemo() async {
    final lat = _centerLat ?? 45.4384;
    final lng = _centerLng ?? 10.9916;
    await FirestoreService.instance.seedSampleEvents(lat: lat, lng: lng);
  }

  Future<void> _toggleFavorite(String id) async {
    final prefs = await SharedPreferences.getInstance();
    if (_favorites.contains(id)) {
      _favorites.remove(id);
    } else {
      _favorites.add(id);
    }
    await prefs.setStringList('favorites', _favorites.toList());
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Eventi Vicini'),
          bottom: const TabBar(
            tabs: [
              Tab(text: 'LISTA'),
              Tab(text: 'MAPPA'),
            ],
          ),
          actions: [
            IconButton(
              onPressed: _seedDemo,
              icon: const Icon(Icons.auto_awesome),
              tooltip: 'Aggiungi 10 eventi demo',
            ),
            PopupMenuButton<double>(
              initialValue: _radiusKm,
              onSelected: (v) => setState(() => _radiusKm = v),
              itemBuilder: (ctx) => const [
                PopupMenuItem(value: 5, child: Text('Raggio 5 km')),
                PopupMenuItem(value: 10, child: Text('Raggio 10 km')),
                PopupMenuItem(value: 25, child: Text('Raggio 25 km')),
                PopupMenuItem(value: 50, child: Text('Raggio 50 km')),
              ],
            ),
          ],
        ),
        body: Column(
          children: [
            FilterBar(
              onlyFree: onlyFree,
              onlyToday: onlyToday,
              onlyWeekend: onlyWeekend,
              onlyKids: onlyKids,
              onFreeChanged: (v) {
                setState(() => onlyFree = v);
                _activeStream = null;
                _subscribeAndLoad();
              },
              onTodayChanged: (v) {
                setState(() {
                  onlyToday = v;
                  if (v) onlyWeekend = false;
                });
                _activeStream = null;
                _subscribeAndLoad();
              },
              onWeekendChanged: (v) {
                setState(() {
                  onlyWeekend = v;
                  if (v) onlyToday = false;
                });
                _activeStream = null;
                _subscribeAndLoad();
              },
              onKidsChanged: (v) {
                setState(() => onlyKids = v);
                _activeStream = null;
                _subscribeAndLoad();
              },
              onSearchSubmitted: _searchAddress,
              searchController: _searchCtl,
            ),
            Expanded(
              child: TabBarView(
                children: [
                  _buildList(),
                  _buildMap(),
                ],
              ),
            ),
          ],
        ),
        floatingActionButton: FloatingActionButton.extended(
          onPressed: () {
            _activeStream = null;
            _subscribeAndLoad();
          },
          icon: const Icon(Icons.refresh),
          label: const Text('Aggiorna eventi'),
        ),
      ),
    );
  }

  Widget _buildList() {
    if (_events.isEmpty) {
      return const Center(
          child: Text('Nessun evento nella zona/periodo selezionato'));
    }
    return ListView.builder(
      itemCount: _events.length,
      itemBuilder: (ctx, i) {
        final ev = _events[i];
        return EventCard(
          event: ev,
          isFavorite: _favorites.contains(ev.id),
          onToggleFavorite: () => _toggleFavorite(ev.id),
          onTap: () => Navigator.of(context).push(
            MaterialPageRoute(
              builder: (_) => EventDetailsPage(event: ev),
            ),
          ),
        );
      },
    );
  }

  Widget _buildMap() {
    final lat = _centerLat ?? 45.4384;
    final lng = _centerLng ?? 10.9916;
    return MapWidget(
      key: const ValueKey('map'),
      cameraOptions: CameraOptions(
        center: Point(coordinates: Position(lng, lat)).toJson(),
        zoom: 11,
      ),
      onMapCreated: _onMapCreated,
    );
  }
}

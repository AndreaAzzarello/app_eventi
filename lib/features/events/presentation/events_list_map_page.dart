import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:geolocator/geolocator.dart';
import 'package:mapbox_maps_flutter/mapbox_maps_flutter.dart';
import '../../events/data/event_service.dart';
import '../../events/domain/event.dart';
import '../../../common/utils/geo.dart';
import 'package:shared_preferences/shared_preferences.dart';

class EventsListMapPage extends StatefulWidget {
  const EventsListMapPage({super.key});
  @override
  State<EventsListMapPage> createState() => _EventsListMapPageState();
}

class _EventsListMapPageState extends State<EventsListMapPage> with TickerProviderStateMixin {
  late final TabController _tab;
  final _svc = EventService();

  List<Event> _events = [];
  bool _loading = true;

  bool _freeOnly = false;
  bool _todayOnly = false;
  bool _weekendOnly = false;
  bool _kidsOnly = false;

  MapboxMap? _map;
  PointAnnotationManager? _pam;
  Position? _userPos;

  @override
  void initState() {
    super.initState();
    _tab = TabController(length: 2, vsync: this);
    _load();
  }

  Future<void> _load() async {
    await _ensurePermissions();
    _userPos ??= await Geolocator.getCurrentPosition();
    final data = await _svc.fetchNearby(
      userLat: _userPos!.latitude,
      userLng: _userPos!.longitude,
      radiusKm: 8,
    );
    setState(() { _events = data; _loading = false; });
    await _refreshMarkers();
  }

  Future<void> _ensurePermissions() async {
    final enabled = await Geolocator.isLocationServiceEnabled();
    if (!enabled && mounted) _snack('Attiva il GPS');

    var p = await Geolocator.checkPermission();
    if (p == LocationPermission.denied) {
      p = await Geolocator.requestPermission();
    }
  }

  List<Event> _applyFilters(List<Event> all) {
    return all.where((e) {
      final okFree = _freeOnly ? e.priceType == 'free' : true;
      final okToday = _todayOnly ? isToday(e.startTime) : true;
      final okWeekend = _weekendOnly ? isWeekend(e.startTime) : true;
      final okKids = _kidsOnly ? e.tags.contains('kids') : true;
      return okFree && okToday && okWeekend && okKids;
    }).toList();
  }

  Future<void> _refreshMarkers() async {
    if (_map == null || _pam == null) return;
    final filtered = _applyFilters(_events);
    await _pam!.deleteAll();
    final opts = filtered.map((e) => PointAnnotationOptions(
      geometry: Point(coordinates: Position(e.lng, e.lat)).toJson(),
      textField: e.title,
      textOffset: [0, -2],
      iconImage: 'marker-15',
    )).toList();
    await _pam!.createMulti(opts);
  }

  @override
  Widget build(BuildContext context) {
    final df = DateFormat('dd-MMM-yyyy HH:mm');
    final filtered = _applyFilters(_events);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Eventi vicini'),
        bottom: TabBar(
          controller: _tab,
          tabs: const [Tab(text: 'Lista'), Tab(text: 'Mappa')],
        ),
        actions: [
          IconButton(
            onPressed: () async { setState(()=>_loading=true); await _load(); },
            icon: const Icon(Icons.refresh),
            tooltip: 'Aggiorna',
          ),
          IconButton(
            onPressed: () async {
              await seedSampleEvents();
              if (!mounted) return;
              _snack('Eventi di prova inseriti');
              setState(()=>_loading=true);
              await _load();
            },
            icon: const Icon(Icons.cloud_upload),
            tooltip: 'Inserisci eventi di prova',
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : TabBarView(
              controller: _tab,
              children: [
                // LISTA
                Column(
                  children: [
                    _filtersBar(),
                    Expanded(
                      child: ListView.builder(
                        itemCount: filtered.length,
                        itemBuilder: (_, i) {
                          final e = filtered[i];
                          return ListTile(
                            title: Text(e.title),
                            subtitle: Text('${e.venueName} • ${df.format(e.startTime)}'),
                            trailing: _FavButton(eventId: e.id),
                            onTap: ()=> _showEventSheet(e),
                          );
                        },
                      ),
                    ),
                  ],
                ),

                // MAPPA
                Stack(
                  children: [
                    MapWidget(
                      styleUri: MapboxStyles.MAPBOX_STREETS,
                      onMapCreated: (controller) async {
                        _map = controller;
                        _pam = await _map!.annotations.createPointAnnotationManager();
                        if (_userPos == null) {
                          await _ensurePermissions();
                          _userPos = await Geolocator.getCurrentPosition();
                        }
                        await _map!.setCamera(
                          CameraOptions(
                            center: Point(coordinates: Position(_userPos!.longitude, _userPos!.latitude)).toJson(),
                            zoom: 13,
                          ),
                        );
                        await _refreshMarkers();
                      },
                    ),
                    Positioned(
                      right: 12, bottom: 12,
                      child: FloatingActionButton.extended(
                        icon: const Icon(Icons.gps_fixed),
                        label: const Text('Centro'),
                        onPressed: () async {
                          if (_userPos == null || _map == null) return;
                          await _map!.flyTo(
                            CameraOptions(
                              center: Point(coordinates: Position(_userPos!.longitude, _userPos!.latitude)).toJson(),
                              zoom: 13,
                            ),
                            const MapAnimationOptions(duration: 600),
                          );
                        },
                      ),
                    ),
                    Positioned(
                      left: 8, right: 8, top: 8,
                      child: Card(
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 8),
                          child: _filtersBar(),
                        ),
                      ),
                    )
                  ],
                ),
              ],
            ),
    );
  }

  Widget _filtersBar() {
    return Wrap(
      spacing: 8,
      children: [
        FilterChip(label: const Text('Gratis'), selected: _freeOnly, onSelected: (v){ setState(()=>_freeOnly=v); _refreshMarkers(); }),
        FilterChip(label: const Text('Oggi'), selected: _todayOnly, onSelected: (v){ setState(()=>_todayOnly=v); _refreshMarkers(); }),
        FilterChip(label: const Text('Weekend'), selected: _weekendOnly, onSelected: (v){ setState(()=>_weekendOnly=v); _refreshMarkers(); }),
        FilterChip(label: const Text('Bambini'), selected: _kidsOnly, onSelected: (v){ setState(()=>_kidsOnly=v); _refreshMarkers(); }),
      ],
    );
  }

  void _showEventSheet(Event e) {
    showModalBottomSheet(
      context: context,
      builder: (_) => Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(e.title, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 6),
            Text(e.shortDescription.isEmpty ? 'Nessuna descrizione' : e.shortDescription),
            const SizedBox(height: 6),
            Text('${e.venueName} • ${e.address}'),
            const SizedBox(height: 6),
            Text('Prezzo: ${e.priceType} • Categoria: ${e.category}'),
            const SizedBox(height: 12),
            Row(
              children: [
                ElevatedButton.icon(
                  onPressed: ()=> Navigator.pop(context),
                  icon: const Icon(Icons.close),
                  label: const Text('Chiudi'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  void _snack(String m) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));
  }
}

class _FavButton extends StatefulWidget {
  final String eventId;
  const _FavButton({required this.eventId});

  @override
  State<_FavButton> createState() => _FavButtonState();
}

class _FavButtonState extends State<_FavButton> {
  static const _k = 'fav_event_ids';
  bool _isFav = false;
  bool _loaded = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final sp = await SharedPreferences.getInstance();
    final set = sp.getStringList(_k)?.toSet() ?? <String>{};
    setState(() { _isFav = set.contains(widget.eventId); _loaded = true; });
  }

  Future<void> _toggle() async {
    final sp = await SharedPreferences.getInstance();
    final set = sp.getStringList(_k)?.toSet() ?? <String>{};
    if (_isFav) {
      set.remove(widget.eventId);
    } else {
      set.add(widget.eventId);
    }
    await sp.setStringList(_k, set.toList());
    setState(() { _isFav = !_isFav; });
  }

  @override
  Widget build(BuildContext context) {
    if (!_loaded) return const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2));
    return IconButton(
      icon: Icon(_isFav ? Icons.favorite : Icons.favorite_border),
      onPressed: _toggle,
    );
  }
}

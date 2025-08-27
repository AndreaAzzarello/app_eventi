import 'package:flutter/material.dart';
import 'package:mapbox_maps_flutter/mapbox_maps_flutter.dart' show CameraOptions, MapOptions, MapWidget, MapboxMap, MapboxStyles, Point, PointAnnotationManager, PointAnnotationOptions, Position, ResourceOptions;
import 'package:geolocator/geolocator.dart' hide Position;

const _mapboxToken = 'pk.eyJ1IjoiYW5kcmVhenphcmVsbG8iLCJhIjoiY21lc295MW1rMDQ5NTJscXY0bHdqN2hvZSJ9.5rX0woMmxCYRDRxtH0RYfw';

class MapPage extends StatefulWidget {
  const MapPage({super.key});

  @override
  State<MapPage> createState() => _MapPageState();
}

class _MapPageState extends State<MapPage> {
  MapboxMap? _map;
  PointAnnotationManager? _pam;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Mappa')),
      body: MapWidget(
        key: const ValueKey("mapWidget"),
        resourceOptions: ResourceOptions(accessToken: _mapboxToken),
        mapOptions: MapOptions(
          pixelRatio: MediaQuery.of(context).devicePixelRatio,
        ),
        styleUri: MapboxStyles.MAPBOX_STREETS,
        onMapCreated: (controller) async {
          _map = controller;
          _pam = await _map!.annotations.createPointAnnotationManager();
          await _ensurePermissionsAndCenter();
        },
      ),
    );
  }

  Future<void> _ensurePermissionsAndCenter() async {
    final serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled && mounted) {
      _showSnack('Attiva il GPS per centrare la mappa');
    }

    var p = await Geolocator.checkPermission();
    if (p == LocationPermission.denied) {
      p = await Geolocator.requestPermission();
    }
    if (p == LocationPermission.denied || p == LocationPermission.deniedForever) {
      // Permessi negati -> fallback Roma
      await _centerAndMark(41.9028, 12.4964, label: 'Roma (fallback)');
      if (p == LocationPermission.deniedForever) {
        _showSnack('Permesso posizione negato permanentemente. Mostro Roma.');
      } else {
        _showSnack('Permessi posizione negati. Mostro Roma.');
      }
      return;
    }

    try {
      final pos = await Geolocator.getCurrentPosition();
      await _centerAndMark(pos.latitude, pos.longitude, label: 'Sei qui');
    } catch (e) {
      await _centerAndMark(41.9028, 12.4964, label: 'Roma (fallback)');
      _showSnack('Impossibile ottenere la posizione. Uso Roma come fallback.');
    }
  }

  Future<void> _centerAndMark(double lat, double lng, {required String label}) async {
    if (_map == null || _pam == null) return;

    final point = Point(coordinates: Position(lng, lat));

    // center accetta una struttura serializzabile: usare toJson() per sicurezza
    await _map!.setCamera(CameraOptions(center: point, zoom: 13));

    // Pulisci eventuali marker precedenti
    try {
      await _pam!.deleteAll();
    } catch (_) {}

    // Aggiungi marker dell'utente
    await _pam!.create(
      PointAnnotationOptions(
        geometry: point,
        textField: label,
        textOffset: [0, -2],
        iconImage: 'marker-15',
      ),
    );
  }

  void _showSnack(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }
}







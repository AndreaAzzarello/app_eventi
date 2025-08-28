import 'package:flutter/material.dart';
import 'package:mapbox_maps_flutter/mapbox_maps_flutter.dart';
import 'package:geolocator/geolocator.dart';

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
      body: MapWidget(
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
    if (!serviceEnabled) _showSnack('Attiva il GPS per centrare la mappa');

    var p = await Geolocator.checkPermission();
    if (p == LocationPermission.denied) {
      p = await Geolocator.requestPermission();
    }
    if (p == LocationPermission.deniedForever) {
      _showSnack('Permesso posizione negato in modo permanente. Apri Impostazioni.');
      await Geolocator.openAppSettings();
    }

    try {
      final pos = await Geolocator.getCurrentPosition();
      await _centerAndMark(pos.latitude, pos.longitude, label: 'Sei qui');
    } catch (_) {
      await _centerAndMark(41.9028, 12.4964, label: 'Roma');
      _showSnack('Uso posizione di default');
    }
  }

  Future<void> _centerAndMark(double lat, double lng, {required String label}) async {
    if (_map == null || _pam == null) return;

    final point = Point(coordinates: Position(lng, lat));

    await _map!.setCamera(CameraOptions(
      center: point.toJson(),
      zoom: 13,
    ));

    await _pam!.deleteAll();

    await _pam!.create(PointAnnotationOptions(
      geometry: point.toJson(),
      iconImage: 'marker-15',
      textField: label,
      textOffset: [0, -2],
    ));
  }

  void _showSnack(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }
}

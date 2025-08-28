import 'package:flutter/material.dart';
import 'package:mapbox_maps_flutter/mapbox_maps_flutter.dart';

class MapPage extends StatefulWidget {
  const MapPage({super.key});

  @override
  State<MapPage> createState() => _MapPageState();
}

class _MapPageState extends State<MapPage> {
  MapboxMap? _map;

  @override
  void initState() {
    super.initState();
    // Se usi --dart-define per il token:
    final token = const String.fromEnvironment('MAPBOX_ACCESS_TOKEN');
    if (token.isNotEmpty) {
      MapboxOptions.setAccessToken(token);
    }
    // Se invece usi la meta-data nel Manifest con @string/mapbox_access_token,
    // puoi non settare nulla qui.
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Mappa')),
      body: MapWidget(
        cameraOptions: const CameraOptions(zoom: 10),
        onMapCreated: (m) => _map = m,
      ),
    );
  }
}

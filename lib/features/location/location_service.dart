import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';

/// Piazza Grande, Modena: usata quando la posizione non è disponibile.
const modenaCenter = LatLng(44.6471, 10.9252);

class UserLocation {
  final LatLng position;
  final bool isFallback;
  const UserLocation(this.position, {this.isFallback = false});
}

class LocationService {
  Future<UserLocation> current() async {
    try {
      if (!await Geolocator.isLocationServiceEnabled()) {
        return const UserLocation(modenaCenter, isFallback: true);
      }
      var perm = await Geolocator.checkPermission();
      if (perm == LocationPermission.denied) {
        perm = await Geolocator.requestPermission();
      }
      if (perm == LocationPermission.denied ||
          perm == LocationPermission.deniedForever) {
        return const UserLocation(modenaCenter, isFallback: true);
      }
      final p = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.medium,
          timeLimit: Duration(seconds: 10),
        ),
      );
      return UserLocation(LatLng(p.latitude, p.longitude));
    } catch (e) {
      debugPrint('Posizione non disponibile: $e');
      return const UserLocation(modenaCenter, isFallback: true);
    }
  }
}

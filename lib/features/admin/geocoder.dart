import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import 'package:latlong2/latlong.dart';

/// Geocoding con Nominatim nel rispetto della policy OSM:
/// User-Agent identificativo, al massimo 1 richiesta al secondo, solo Italia.
class NominatimGeocoder {
  final http.Client _client;
  DateTime _last = DateTime.fromMillisecondsSinceEpoch(0);

  NominatimGeocoder([http.Client? client]) : _client = client ?? http.Client();

  Future<LatLng?> geocode(String address) async {
    final wait = _last.add(const Duration(seconds: 1)).difference(DateTime.now());
    if (wait > Duration.zero) await Future<void>.delayed(wait);
    _last = DateTime.now();

    final uri = Uri.https('nominatim.openstreetmap.org', '/search', {
      'q': address,
      'format': 'jsonv2',
      'limit': '1',
      'countrycodes': 'it',
      'accept-language': 'it',
    });
    // Il browser non permette di impostare User-Agent: sul web vale il Referer.
    final res = await _client.get(uri,
        headers: kIsWeb ? null : {'User-Agent': 'EventiVicini/1.0 (app_eventi admin)'});
    if (res.statusCode != 200) {
      throw http.ClientException('Nominatim ha risposto ${res.statusCode}', uri);
    }
    final list = jsonDecode(res.body) as List;
    if (list.isEmpty) return null;
    final m = list.first as Map<String, dynamic>;
    return LatLng(double.parse('${m['lat']}'), double.parse('${m['lon']}'));
  }
}

final geocoderProvider = Provider((ref) => NominatimGeocoder());

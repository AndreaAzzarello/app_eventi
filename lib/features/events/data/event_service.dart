import 'package:cloud_firestore/cloud_firestore.dart';
import '../../events/domain/event.dart';
import '../../../common/utils/geo.dart';

class EventService {
  final _fs = FirebaseFirestore.instance;

  Future<List<Event>> fetchAll() async {
    final snap = await _fs.collection('events').get();
    return snap.docs.map((d) => Event.fromMap(d.id, d.data())).toList();
  }

  Future<List<Event>> fetchNearby({
    required double userLat,
    required double userLng,
    double radiusKm = 8,
  }) async {
    final all = await fetchAll();
    return all.where((e) {
      final dist = haversineKm(userLat, userLng, e.lat, e.lng);
      return dist <= radiusKm;
    }).toList()
    ..sort((a,b){
      final da = haversineKm(userLat, userLng, a.lat, a.lng);
      final db = haversineKm(userLat, userLng, b.lat, b.lng);
      return da.compareTo(db);
    });
  }
}

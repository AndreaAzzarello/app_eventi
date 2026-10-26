import 'package:cloud_firestore/cloud_firestore.dart';
import '../../events/domain/event.dart';

class EventService {
  final _fs = FirebaseFirestore.instance;

  CollectionReference<Map<String, dynamic>> get _events =>
      _fs.collection('events');

  /// Eventi non ancora finiti, in tempo reale. Filtra su endTime (non startTime)
  /// così restano visibili mostre e eventi di più giorni già iniziati.
  /// shortcut: limit fisso per stare nella quota letture Spark, paginare se gli eventi crescono.
  Stream<List<Event>> watchUpcoming() => _events
      .where('endTime', isGreaterThanOrEqualTo: DateTime.now().millisecondsSinceEpoch)
      .orderBy('endTime')
      .limit(500)
      .snapshots()
      .map(_toEvents);

  /// Tutti gli eventi, anche passati, per l'area admin.
  Stream<List<Event>> watchAll() => _events
      .orderBy('startTime', descending: true)
      .snapshots()
      .map(_toEvents);

  static List<Event> _toEvents(QuerySnapshot<Map<String, dynamic>> snap) =>
      snap.docs.map((d) => Event.fromMap(d.id, d.data())).toList();
}

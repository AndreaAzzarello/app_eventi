import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../events/data/event_service.dart';
import '../events/domain/event.dart';

/// Scritture dell'area admin. Le regole Firestore le permettono solo all'admin.
class AdminRepository {
  CollectionReference<Map<String, dynamic>> get _events =>
      FirebaseFirestore.instance.collection('events');

  /// Crea se id è vuoto, altrimenti aggiorna. Restituisce l'id del documento.
  Future<String> save(Event e) async {
    final doc = e.id.isEmpty ? _events.doc() : _events.doc(e.id);
    await doc.set(e.toMap());
    return doc.id;
  }

  Future<void> delete(String id) => _events.doc(id).delete();
}

final adminRepositoryProvider = Provider((ref) => AdminRepository());

/// Tutti gli eventi, anche passati, più recenti prima.
final allEventsProvider =
    StreamProvider<List<Event>>((ref) => EventService().watchAll());

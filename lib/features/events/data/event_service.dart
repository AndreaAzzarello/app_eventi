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
      final d = haversineKm(userLat, userLng, e.lat, e.lng);
      return d <= radiusKm;
    }).toList()
      ..sort((a, b) {
        final da = haversineKm(userLat, userLng, a.lat, a.lng);
        final db = haversineKm(userLat, userLng, b.lat, b.lng);
        return da.compareTo(db);
      });
  }
}

/// Inserisce 10 eventi di prova nella collezione 'events'
Future<void> seedSampleEvents() async {
  final fs = FirebaseFirestore.instance;
  final batch = fs.batch();
  final coll = fs.collection('events');

  final now = DateTime.now();
  final samples = [
    {
      "title": "Concerto in piazza",
      "shortDescription": "Live gratuito",
      "category": "music",
      "priceType": "free",
      "startTime": now.add(const Duration(hours: 6)).millisecondsSinceEpoch,
      "endTime":  now.add(const Duration(hours: 8)).millisecondsSinceEpoch,
      "venueName": "Piazza Roma",
      "address": "Piazza Roma, Modena",
      "lat": 44.646, "lng": 10.925,
      "imageUrl": "", "ticketUrl": "",
      "tags": ["outdoor","live","kids"]
    },
    {
      "title": "Sagra del quartiere",
      "shortDescription": "Street food e musica",
      "category": "food",
      "priceType": "low",
      "startTime": now.add(const Duration(days: 1, hours: 2)).millisecondsSinceEpoch,
      "endTime":  now.add(const Duration(days: 1, hours: 6)).millisecondsSinceEpoch,
      "venueName": "Parco Ducale",
      "address": "Parco Ducale, Modena",
      "lat": 44.650, "lng": 10.930,
      "imageUrl": "", "ticketUrl": "",
      "tags": ["outdoor","family"]
    },
    {
      "title": "Mostra d'arte contemporanea",
      "shortDescription": "Ingresso gratuito fino alle 18",
      "category": "culture",
      "priceType": "free",
      "startTime": now.add(const Duration(days: 2)).millisecondsSinceEpoch,
      "endTime":  now.add(const Duration(days: 2, hours: 3)).millisecondsSinceEpoch,
      "venueName": "Galleria Civica",
      "address": "Via Emilia, Modena",
      "lat": 44.645, "lng": 10.922,
      "imageUrl": "", "ticketUrl": "",
      "tags": ["indoor"]
    },
    {
      "title": "Mercatino dell'antiquariato",
      "shortDescription": "Bancarelle e artigianato",
      "category": "market",
      "priceType": "free",
      "startTime": now.add(const Duration(days: 3, hours: 1)).millisecondsSinceEpoch,
      "endTime":  now.add(const Duration(days: 3, hours: 5)).millisecondsSinceEpoch,
      "venueName": "Piazza Grande",
      "address": "Piazza Grande, Modena",
      "lat": 44.6455, "lng": 10.9255,
      "imageUrl": "", "ticketUrl": "",
      "tags": ["outdoor","kids"]
    },
    {
      "title": "Allenamento aperto corsa",
      "shortDescription": "5km nel parco",
      "category": "sport",
      "priceType": "free",
      "startTime": now.add(const Duration(days: 1, hours: 20)).millisecondsSinceEpoch,
      "endTime":  now.add(const Duration(days: 1, hours: 22)).millisecondsSinceEpoch,
      "venueName": "Parco Ferrari",
      "address": "Parco Ferrari, Modena",
      "lat": 44.640, "lng": 10.926,
      "imageUrl": "", "ticketUrl": "",
      "tags": ["outdoor"]
    },
    {
      "title": "Laboratorio bambini",
      "shortDescription": "Giochi creativi 6-10 anni",
      "category": "kids",
      "priceType": "free",
      "startTime": now.add(const Duration(days: 4, hours: 10)).millisecondsSinceEpoch,
      "endTime":  now.add(const Duration(days: 4, hours: 12)).millisecondsSinceEpoch,
      "venueName": "Biblioteca comunale",
      "address": "Via dei Mille, Modena",
      "lat": 44.643, "lng": 10.920,
      "imageUrl": "", "ticketUrl": "",
      "tags": ["kids","indoor"]
    },
    {
      "title": "Degustazione prodotti tipici",
      "shortDescription": "Aceto balsamico & more",
      "category": "food",
      "priceType": "premium",
      "startTime": now.add(const Duration(days: 5, hours: 18)).millisecondsSinceEpoch,
      "endTime":  now.add(const Duration(days: 5, hours: 20)).millisecondsSinceEpoch,
      "venueName": "Cortile Estense",
      "address": "Largo Porta Sant'Agostino, Modena",
      "lat": 44.6468, "lng": 10.9212,
      "imageUrl": "", "ticketUrl": "",
      "tags": ["outdoor"]
    },
    {
      "title": "Cinema all'aperto",
      "shortDescription": "Classico restaurato",
      "category": "culture",
      "priceType": "low",
      "startTime": now.add(const Duration(days: 2, hours: 21)).millisecondsSinceEpoch,
      "endTime":  now.add(const Duration(days: 2, hours: 23, minutes: 30)).millisecondsSinceEpoch,
      "venueName": "Arena estiva",
      "address": "Via del Cinema, Modena",
      "lat": 44.6473, "lng": 10.9281,
      "imageUrl": "", "ticketUrl": "",
      "tags": ["outdoor"]
    },
    {
      "title": "Concerto acustico",
      "shortDescription": "Ingresso libero con prenotazione",
      "category": "music",
      "priceType": "free",
      "startTime": now.add(const Duration(days: 6, hours: 19)).millisecondsSinceEpoch,
      "endTime":  now.add(const Duration(days: 6, hours: 21)).millisecondsSinceEpoch,
      "venueName": "Chiostro San Pietro",
      "address": "Via San Pietro, Modena",
      "lat": 44.6422, "lng": 10.9197,
      "imageUrl": "", "ticketUrl": "",
      "tags": ["outdoor","live"]
    },
    {
      "title": "Corso gratuito fotografia",
      "shortDescription": "Base per principianti",
      "category": "culture",
      "priceType": "free",
      "startTime": now.add(const Duration(days: 7, hours: 17)).millisecondsSinceEpoch,
      "endTime":  now.add(const Duration(days: 7, hours: 19)).millisecondsSinceEpoch,
      "venueName": "Centro Civico",
      "address": "Via Emilia Ovest, Modena",
      "lat": 44.6389, "lng": 10.9184,
      "imageUrl": "", "ticketUrl": "",
      "tags": ["indoor"]
    },
  ];

  for (final e in samples) {
    batch.set(coll.doc(), e);
  }
  await batch.commit();
}

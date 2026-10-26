import 'package:cloud_firestore/cloud_firestore.dart' show Timestamp;

class Event {
  final String id;
  final String title;
  final String shortDescription;
  final String category;   // music, food, sport, culture, kids, market, other
  final String priceType;  // free, low, premium
  final DateTime startTime;
  final DateTime endTime;
  final String venueName;
  final String address;
  final double lat;
  final double lng;
  final String imageUrl;
  final String ticketUrl;
  final List<String> tags;

  Event({
    required this.id,
    required this.title,
    required this.shortDescription,
    required this.category,
    required this.priceType,
    required this.startTime,
    required this.endTime,
    required this.venueName,
    required this.address,
    required this.lat,
    required this.lng,
    required this.imageUrl,
    required this.ticketUrl,
    required this.tags,
  });

  bool get isFree => priceType == 'free';
  bool get isForKids =>
      category == 'kids' || tags.contains('kids') || tags.contains('family');

  factory Event.fromMap(String id, Map<String, dynamic> m) {
    DateTime ts(dynamic v) {
      if (v is DateTime) return v;
      if (v is Timestamp) return v.toDate();
      if (v is int) return DateTime.fromMillisecondsSinceEpoch(v);
      return DateTime.tryParse('$v') ?? DateTime.now();
    }

    final start = ts(m['startTime']);
    return Event(
      id: id,
      title: (m['title'] ?? '').toString(),
      shortDescription: (m['shortDescription'] ?? '').toString(),
      category: (m['category'] ?? 'other').toString(),
      priceType: (m['priceType'] ?? 'free').toString(),
      startTime: start,
      endTime: m['endTime'] == null ? start : ts(m['endTime']),
      venueName: (m['venueName'] ?? '').toString(),
      address: (m['address'] ?? '').toString(),
      lat: (m['lat'] as num?)?.toDouble() ?? 0,
      lng: (m['lng'] as num?)?.toDouble() ?? 0,
      imageUrl: (m['imageUrl'] ?? '').toString(),
      ticketUrl: (m['ticketUrl'] ?? '').toString(),
      tags: [for (final t in (m['tags'] as List?) ?? const []) '$t'],
    );
  }

  Map<String, dynamic> toMap() => {
    'title': title,
    'shortDescription': shortDescription,
    'category': category,
    'priceType': priceType,
    'startTime': startTime.millisecondsSinceEpoch,
    'endTime': endTime.millisecondsSinceEpoch,
    'venueName': venueName,
    'address': address,
    'lat': lat,
    'lng': lng,
    'imageUrl': imageUrl,
    'ticketUrl': ticketUrl,
    'tags': tags,
  };
}

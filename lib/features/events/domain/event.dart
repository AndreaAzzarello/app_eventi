class Event {
  final String id;
  final String title;
  final String shortDescription;
  final String category;   // music, food, sport, culture, kids, other
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

  factory Event.fromMap(String id, Map<String, dynamic> m) {
    DateTime ts(dynamic v) {
      if (v is DateTime) return v;
      if (v is int) return DateTime.fromMillisecondsSinceEpoch(v);
      final s = v.toString();
      return DateTime.tryParse(s) ?? DateTime.now();
    }

    return Event(
      id: id,
      title: (m['title'] ?? '').toString(),
      shortDescription: (m['shortDescription'] ?? '').toString(),
      category: (m['category'] ?? 'other').toString(),
      priceType: (m['priceType'] ?? 'free').toString(),
      startTime: ts(m['startTime']),
      endTime: ts(m['endTime']),
      venueName: (m['venueName'] ?? '').toString(),
      address: (m['address'] ?? '').toString(),
      lat: (m['lat'] as num).toDouble(),
      lng: (m['lng'] as num).toDouble(),
      imageUrl: (m['imageUrl'] ?? '').toString(),
      ticketUrl: (m['ticketUrl'] ?? '').toString(),
      tags: List<String>.from(m['tags'] ?? const []),
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

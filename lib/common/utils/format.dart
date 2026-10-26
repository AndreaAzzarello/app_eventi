import 'package:intl/intl.dart';

String _cap(String s) => s.isEmpty ? s : s[0].toUpperCase() + s.substring(1);

/// "Sab 1 nov · 21:00"
String shortWhen(DateTime d) =>
    '${_cap(DateFormat('EEE d MMM', 'it_IT').format(d))} · ${DateFormat.Hm('it_IT').format(d)}';

/// "Sabato 1 novembre 2026"
String longDate(DateTime d) =>
    _cap(DateFormat('EEEE d MMMM y', 'it_IT').format(d));

/// "21:00 – 23:30"
String timeRange(DateTime a, DateTime b) =>
    '${DateFormat.Hm('it_IT').format(a)} – ${DateFormat.Hm('it_IT').format(b)}';

String distanceLabel(double km) => km < 1
    ? '${(km * 1000).round()} m'
    : '${NumberFormat('0.0', 'it_IT').format(km)} km';

String priceLabel(String priceType) => switch (priceType) {
      'free' => 'Gratis',
      'low' => '€',
      'premium' => '€€€',
      _ => priceType,
    };

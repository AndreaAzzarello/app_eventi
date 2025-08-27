import 'dart:math';

double haversineKm(double lat1, double lon1, double lat2, double lon2) {
  const R = 6371.0;
  double dLat = (lat2 - lat1) * pi / 180.0;
  double dLon = (lon2 - lon1) * pi / 180.0;
  double a = sin(dLat/2) * sin(dLat/2) +
             cos(lat1*pi/180.0) * cos(lat2*pi/180.0) *
             sin(dLon/2) * sin(dLon/2);
  double c = 2 * atan2(sqrt(a), sqrt(1-a));
  return R * c;
}

bool isToday(DateTime dt) {
  final now = DateTime.now();
  return dt.year == now.year && dt.month == now.month && dt.day == now.day;
}

bool isWeekend(DateTime dt) {
  return dt.weekday == DateTime.saturday || dt.weekday == DateTime.sunday;
}

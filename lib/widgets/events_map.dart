import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:url_launcher/url_launcher.dart';

import '../app/theme.dart';
import '../features/events/domain/event.dart';

class EventsMap extends StatelessWidget {
  final List<Event> events;
  final LatLng center;
  final bool showUser;
  final ValueChanged<Event> onEventTap;

  const EventsMap({
    super.key,
    required this.events,
    required this.center,
    required this.onEventTap,
    this.showUser = true,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return FlutterMap(
      // La key ricentra la mappa quando arriva la posizione reale.
      key: ValueKey(center),
      options: MapOptions(initialCenter: center, initialZoom: 13),
      children: [
        TileLayer(
          urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
          userAgentPackageName: 'com.example.app_eventi',
          maxNativeZoom: 19,
        ),
        MarkerLayer(markers: [
          if (showUser)
            Marker(
              point: center,
              width: 22,
              height: 22,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: scheme.primary,
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.white, width: 3),
                  boxShadow: const [
                    BoxShadow(blurRadius: 6, color: Colors.black26)
                  ],
                ),
              ),
            ),
          for (final e in events)
            Marker(
              point: LatLng(e.lat, e.lng),
              width: 40,
              height: 40,
              alignment: Alignment.topCenter,
              child: _Pin(event: e, onTap: () => onEventTap(e)),
            ),
        ]),
        RichAttributionWidget(
          attributions: [
            TextSourceAttribution(
              'OpenStreetMap contributors',
              onTap: () => launchUrl(
                  Uri.parse('https://www.openstreetmap.org/copyright')),
            ),
          ],
        ),
      ],
    );
  }
}

class _Pin extends StatelessWidget {
  final Event event;
  final VoidCallback onTap;
  const _Pin({required this.event, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final style = categoryStyle(event.category);
    return Tooltip(
      message: event.title,
      child: GestureDetector(
        onTap: onTap,
        child: Stack(alignment: Alignment.topCenter, children: [
          Icon(Icons.location_on, size: 40, color: style.color, shadows: const [
            Shadow(blurRadius: 4, color: Colors.black38),
          ]),
          Padding(
            padding: const EdgeInsets.only(top: 7),
            child: Icon(style.icon, size: 15, color: Colors.white),
          ),
        ]),
      ),
    );
  }
}

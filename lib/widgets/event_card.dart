import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../app/theme.dart';
import '../common/utils/format.dart';
import '../features/events/domain/event.dart';

/// Immagine dell'evento, o un placeholder col colore e l'icona della categoria.
class EventImage extends StatelessWidget {
  final Event event;
  final double iconSize;
  const EventImage({super.key, required this.event, this.iconSize = 40});

  @override
  Widget build(BuildContext context) {
    final style = categoryStyle(event.category);
    final placeholder = DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [style.color, Color.lerp(style.color, Colors.black, 0.35)!],
        ),
      ),
      child: Center(
        child: Icon(style.icon,
            size: iconSize, color: Colors.white.withValues(alpha: 0.85)),
      ),
    );
    if (event.imageUrl.isEmpty) return placeholder;
    return CachedNetworkImage(
      imageUrl: event.imageUrl,
      fit: BoxFit.cover,
      placeholder: (_, _) => placeholder,
      errorWidget: (_, _, _) => placeholder,
    );
  }
}

class EventCard extends StatelessWidget {
  final Event event;
  final bool isFavorite;
  final double? distanceKm;
  final VoidCallback onTap;
  final VoidCallback onToggleFavorite;

  const EventCard({
    super.key,
    required this.event,
    required this.isFavorite,
    required this.onTap,
    required this.onToggleFavorite,
    this.distanceKm,
  });

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final style = categoryStyle(event.category);
    final muted = t.textTheme.bodySmall
        ?.copyWith(color: t.colorScheme.onSurfaceVariant);

    return Card(
      child: InkWell(
        onTap: onTap,
        child: SizedBox(
          height: 128,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              SizedBox(
                width: 112,
                child: Hero(
                    tag: 'event-image-${event.id}',
                    child: EventImage(event: event, iconSize: 36)),
              ),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 14, 4, 12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        shortWhen(event.startTime).toUpperCase(),
                        style: t.textTheme.labelSmall
                            ?.copyWith(color: style.color),
                      ),
                      const SizedBox(height: 4),
                      Text(event.title,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: t.textTheme.titleMedium),
                      const Spacer(),
                      Text(
                        event.venueName.isNotEmpty
                            ? event.venueName
                            : event.address,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: muted,
                      ),
                      const SizedBox(height: 2),
                      Text(
                        [
                          priceLabel(event.priceType),
                          if (distanceKm != null) distanceLabel(distanceKm!),
                        ].join(' · '),
                        style: muted?.copyWith(fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
              ),
              Align(
                alignment: Alignment.topCenter,
                child: IconButton(
                  tooltip: isFavorite
                      ? 'Rimuovi dai preferiti'
                      : 'Aggiungi ai preferiti',
                  onPressed: onToggleFavorite,
                  icon: Icon(
                    isFavorite
                        ? Icons.favorite_rounded
                        : Icons.favorite_border_rounded,
                    color: isFavorite ? t.colorScheme.primary : null,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../app/theme.dart';
import '../common/utils/format.dart';
import '../features/calendar/calendar_service.dart';
import '../features/events/application/providers.dart';
import '../features/events/domain/event.dart';
import '../widgets/event_card.dart';

class EventDetailsPage extends ConsumerWidget {
  final Event event;
  const EventDetailsPage({super.key, required this.event});

  Future<void> _open(BuildContext context, Uri uri) async {
    final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
    if (!ok && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Impossibile aprire il link')));
    }
  }

  Future<void> _addToCalendar(BuildContext context) async {
    var ok = false;
    try {
      ok = await addToCalendar(event);
    } catch (e) {
      debugPrint('Calendario: $e');
    }
    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(ok
            ? 'Evento pronto per il calendario'
            : 'Non è stato possibile aggiungere l\'evento')));
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = Theme.of(context);
    final style = categoryStyle(event.category);
    final isFav =
        ref.watch(favoritesProvider).value?.contains(event.id) ?? false;
    final tickets = Uri.tryParse(event.ticketUrl);
    final mapsUri = Uri.https('www.google.com', '/maps/search/', {
      'api': '1',
      'query': '${event.lat},${event.lng}',
    });

    return Scaffold(
      body: CustomScrollView(slivers: [
        SliverAppBar(
          pinned: true,
          expandedHeight: 280,
          actions: [
            IconButton.filledTonal(
              tooltip:
                  isFav ? 'Rimuovi dai preferiti' : 'Aggiungi ai preferiti',
              onPressed: () =>
                  ref.read(favoritesProvider.notifier).toggle(event.id),
              icon: Icon(isFav
                  ? Icons.favorite_rounded
                  : Icons.favorite_border_rounded),
            ),
            const SizedBox(width: 8),
          ],
          flexibleSpace: FlexibleSpaceBar(
            background: Hero(
              tag: 'event-image-${event.id}',
              child: EventImage(event: event, iconSize: 96),
            ),
          ),
        ),
        SliverToBoxAdapter(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 720),
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 20, 20, 40),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Wrap(spacing: 8, children: [
                      Chip(
                        avatar: Icon(style.icon, size: 18, color: style.color),
                        label: Text(style.label),
                      ),
                      Chip(label: Text(priceLabel(event.priceType))),
                    ]),
                    const SizedBox(height: 12),
                    Text(event.title, style: t.textTheme.headlineMedium),
                    if (event.shortDescription.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Text(event.shortDescription,
                          style: t.textTheme.bodyLarge?.copyWith(
                              color: t.colorScheme.onSurfaceVariant)),
                    ],
                    const SizedBox(height: 24),
                    _InfoRow(
                      icon: Icons.calendar_today_rounded,
                      title: longDate(event.startTime),
                      subtitle: timeRange(event.startTime, event.endTime),
                    ),
                    _InfoRow(
                      icon: Icons.place_rounded,
                      title: event.venueName.isNotEmpty
                          ? event.venueName
                          : event.address,
                      subtitle:
                          event.venueName.isNotEmpty ? event.address : null,
                    ),
                    const SizedBox(height: 24),
                    Wrap(spacing: 12, runSpacing: 12, children: [
                      FilledButton.icon(
                        onPressed: () => _addToCalendar(context),
                        icon: const Icon(Icons.event_available_rounded),
                        label: const Text('Aggiungi al calendario'),
                      ),
                      OutlinedButton.icon(
                        onPressed: () => _open(context, mapsUri),
                        icon: const Icon(Icons.map_rounded),
                        label: const Text('Apri in Maps'),
                      ),
                      // Solo link web: il dato arriva da Firestore.
                      if (tickets != null &&
                          (tickets.isScheme('https') ||
                              tickets.isScheme('http')))
                        OutlinedButton.icon(
                          onPressed: () => _open(context, tickets),
                          icon: const Icon(Icons.confirmation_number_rounded),
                          label: const Text('Biglietti'),
                        ),
                    ]),
                  ],
                ),
              ),
            ),
          ),
        ),
      ]),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String title;
  final String? subtitle;
  const _InfoRow({required this.icon, required this.title, this.subtitle});

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: t.colorScheme.primaryContainer,
            borderRadius: BorderRadius.circular(14),
          ),
          child: Icon(icon, size: 20, color: t.colorScheme.onPrimaryContainer),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, style: t.textTheme.titleMedium),
            if (subtitle != null)
              Text(subtitle!,
                  style: t.textTheme.bodyMedium
                      ?.copyWith(color: t.colorScheme.onSurfaceVariant)),
          ]),
        ),
      ]),
    );
  }
}

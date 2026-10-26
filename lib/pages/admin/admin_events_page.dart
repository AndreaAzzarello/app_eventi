import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../common/utils/format.dart';
import '../../features/admin/admin_repository.dart';
import '../../features/auth/auth.dart';
import '../../features/events/domain/event.dart';
import '../../widgets/state_views.dart';

/// Lista di tutti gli eventi (anche passati) con ricerca, modifica ed eliminazione.
class AdminEventsPage extends ConsumerStatefulWidget {
  const AdminEventsPage({super.key});

  @override
  ConsumerState<AdminEventsPage> createState() => _AdminEventsPageState();
}

class _AdminEventsPageState extends ConsumerState<AdminEventsPage> {
  String _query = '';

  Future<void> _delete(Event e) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        icon: const Icon(Icons.delete_outline_rounded),
        title: const Text('Eliminare l\'evento?'),
        content: Text('"${e.title}" verrà rimosso definitivamente.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Annulla')),
          FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('Elimina')),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    final messenger = ScaffoldMessenger.of(context);
    try {
      await ref.read(adminRepositoryProvider).delete(e.id);
      messenger.showSnackBar(SnackBar(content: Text('Eliminato "${e.title}"')));
    } catch (err) {
      messenger.showSnackBar(
          SnackBar(content: Text('Eliminazione non riuscita: $err')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final email = ref.watch(authStateProvider).value?.email ?? '';
    return Scaffold(
      appBar: AppBar(
        title: const Text('Area admin'),
        leading: IconButton(
          tooltip: 'Torna agli eventi',
          onPressed: () => context.go('/'),
          icon: const Icon(Icons.arrow_back_rounded),
        ),
        actions: [
          IconButton(
            tooltip: 'Esci ($email)',
            onPressed: signOut,
            icon: const Icon(Icons.logout_rounded),
          ),
          const SizedBox(width: 8),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.push('/admin/events/new'),
        icon: const Icon(Icons.add_rounded),
        label: const Text('Nuovo evento'),
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 720),
          child: Column(children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
              child: TextField(
                onChanged: (v) => setState(() => _query = v.trim().toLowerCase()),
                decoration: const InputDecoration(
                  hintText: 'Cerca per titolo, luogo o indirizzo',
                  prefixIcon: Icon(Icons.search_rounded),
                ),
              ),
            ),
            Expanded(
              child: ref.watch(allEventsProvider).when(
                    loading: () => const LoadingView(),
                    error: (e, _) => MessageView(
                      icon: Icons.cloud_off_rounded,
                      title: 'Impossibile caricare gli eventi',
                      message: '$e',
                      action: FilledButton.tonal(
                        onPressed: () => ref.invalidate(allEventsProvider),
                        child: const Text('Riprova'),
                      ),
                    ),
                    data: (all) {
                      final events = [
                        for (final e in all)
                          if ('${e.title} ${e.venueName} ${e.address}'
                              .toLowerCase()
                              .contains(_query))
                            e
                      ];
                      if (events.isEmpty) {
                        return MessageView(
                          icon: Icons.event_note_rounded,
                          title: all.isEmpty
                              ? 'Ancora nessun evento'
                              : 'Nessun risultato',
                          message: all.isEmpty
                              ? 'Crea il primo con "Nuovo evento".'
                              : 'Prova con un\'altra ricerca.',
                        );
                      }
                      return ListView.separated(
                        padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
                        itemCount: events.length,
                        separatorBuilder: (_, _) => const SizedBox(height: 8),
                        itemBuilder: (_, i) => _AdminEventTile(
                          event: events[i],
                          onEdit: () =>
                              context.push('/admin/events/${events[i].id}'),
                          onDelete: () => _delete(events[i]),
                        ),
                      );
                    },
                  ),
            ),
          ]),
        ),
      ),
    );
  }
}

class _AdminEventTile extends StatelessWidget {
  final Event event;
  final VoidCallback onEdit;
  final VoidCallback onDelete;
  const _AdminEventTile(
      {required this.event, required this.onEdit, required this.onDelete});

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final style = categoryStyle(event.category);
    final past = event.endTime.isBefore(DateTime.now());
    return Card(
      child: ListTile(
        onTap: onEdit,
        contentPadding: const EdgeInsets.fromLTRB(16, 4, 4, 4),
        leading: CircleAvatar(
          backgroundColor: style.color.withValues(alpha: 0.15),
          child: Icon(style.icon, color: style.color),
        ),
        title: Text(event.title,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: past
                ? TextStyle(color: t.colorScheme.onSurfaceVariant)
                : null),
        subtitle: Text(
          [
            shortWhen(event.startTime),
            if (event.venueName.isNotEmpty) event.venueName,
            if (past) 'Passato',
            if (event.source == 'scraper') 'Import',
          ].join(' · '),
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
        trailing: IconButton(
          tooltip: 'Elimina',
          onPressed: onDelete,
          icon: const Icon(Icons.delete_outline_rounded),
        ),
      ),
    );
  }
}

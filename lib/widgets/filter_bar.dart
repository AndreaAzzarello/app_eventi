import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../app/theme.dart';
import '../features/events/application/providers.dart';
import '../features/events/domain/event_filter.dart';

class FilterBar extends ConsumerStatefulWidget {
  const FilterBar({super.key});

  @override
  ConsumerState<FilterBar> createState() => _FilterBarState();
}

class _FilterBarState extends ConsumerState<FilterBar> {
  late final _search =
      TextEditingController(text: ref.read(eventFilterProvider).query);

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final f = ref.watch(eventFilterProvider);
    final n = ref.read(eventFilterProvider.notifier);
    final t = Theme.of(context);

    Widget chip(String label, bool selected, VoidCallback onTap) => Padding(
          padding: const EdgeInsets.only(right: 8),
          child: FilterChip(
              label: Text(label),
              selected: selected,
              onSelected: (_) => onTap()),
        );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
          child: TextField(
            controller: _search,
            onChanged: n.setQuery,
            textInputAction: TextInputAction.search,
            decoration: InputDecoration(
              hintText: 'Cerca eventi, luoghi…',
              prefixIcon: const Icon(Icons.search_rounded),
              suffixIcon: f.query.isEmpty
                  ? null
                  : IconButton(
                      tooltip: 'Cancella ricerca',
                      icon: const Icon(Icons.close_rounded),
                      onPressed: () {
                        _search.clear();
                        n.setQuery('');
                      },
                    ),
            ),
          ),
        ),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Row(children: [
            chip('Oggi', f.window == DateWindow.today,
                () => n.toggleWindow(DateWindow.today)),
            chip('Weekend', f.window == DateWindow.weekend,
                () => n.toggleWindow(DateWindow.weekend)),
            chip('Gratis', f.onlyFree, n.toggleFree),
            chip('Bambini', f.onlyKids, n.toggleKids),
            Container(
                width: 1,
                height: 24,
                margin: const EdgeInsets.only(right: 8),
                color: t.colorScheme.outlineVariant),
            for (final MapEntry(key: id, value: c) in categories.entries)
              Padding(
                padding: const EdgeInsets.only(right: 8),
                child: ChoiceChip(
                  avatar: Icon(c.icon, size: 18, color: c.color),
                  label: Text(c.label),
                  selected: f.category == id,
                  onSelected: (sel) => n.setCategory(sel ? id : null),
                ),
              ),
          ]),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 4, 8, 0),
          child: Row(children: [
            Icon(Icons.radar_rounded,
                size: 20, color: t.colorScheme.onSurfaceVariant),
            Expanded(
              child: Slider(
                value: f.radiusKm,
                min: 1,
                max: 50,
                divisions: 49,
                label: '${f.radiusKm.round()} km',
                onChanged: n.setRadius,
              ),
            ),
            SizedBox(
              width: 56,
              child: Text('${f.radiusKm.round()} km',
                  style: t.textTheme.labelLarge),
            ),
          ]),
        ),
      ],
    );
  }
}

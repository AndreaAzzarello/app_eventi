import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:latlong2/latlong.dart';

import '../../app/theme.dart';
import '../../common/utils/format.dart';
import '../../features/admin/admin_repository.dart';
import '../../features/admin/event_form_validators.dart';
import '../../features/admin/geocoder.dart';
import '../../features/events/domain/event.dart';
import '../../features/location/location_service.dart';
import '../../widgets/state_views.dart';

/// Crea (eventId null) o modifica un evento. Con l'id carica l'evento dallo stream,
/// così anche un URL `/admin/events/<id>` aperto a freddo funziona.
class EventFormPage extends ConsumerWidget {
  final String? eventId;
  const EventFormPage({super.key, this.eventId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (eventId == null) return const _EventForm();
    return ref.watch(allEventsProvider).when(
          loading: () => const Scaffold(body: LoadingView()),
          error: (e, _) => Scaffold(
            appBar: AppBar(),
            body: MessageView(
                icon: Icons.cloud_off_rounded,
                title: 'Impossibile caricare l\'evento',
                message: '$e'),
          ),
          data: (all) {
            final e = all.where((e) => e.id == eventId).firstOrNull;
            if (e == null) {
              return Scaffold(
                appBar: AppBar(),
                body: const MessageView(
                    icon: Icons.search_off_rounded,
                    title: 'Evento non trovato',
                    message: 'Potrebbe essere stato eliminato.'),
              );
            }
            return _EventForm(initial: e);
          },
        );
  }
}

class _EventForm extends ConsumerStatefulWidget {
  final Event? initial;
  const _EventForm({this.initial});

  @override
  ConsumerState<_EventForm> createState() => _EventFormState();
}

class _EventFormState extends ConsumerState<_EventForm> {
  final _formKey = GlobalKey<FormState>();
  final _map = MapController();
  late final _title = TextEditingController(text: widget.initial?.title);
  late final _description =
      TextEditingController(text: widget.initial?.shortDescription);
  late final _venue = TextEditingController(text: widget.initial?.venueName);
  late final _address = TextEditingController(text: widget.initial?.address);
  late final _image = TextEditingController(text: widget.initial?.imageUrl);
  late final _ticket = TextEditingController(text: widget.initial?.ticketUrl);
  late final _tags = TextEditingController(
      text: widget.initial?.tags.where((t) => t != 'kids').join(', '));

  late String _category = widget.initial?.category ?? 'other';
  late String _price = widget.initial?.priceType ?? 'free';
  late bool _kids = widget.initial?.tags.contains('kids') ?? false;
  late DateTime _start = widget.initial?.startTime ?? _defaultStart();
  late DateTime _end =
      widget.initial?.endTime ?? _start.add(const Duration(hours: 2));
  late LatLng? _pin = widget.initial == null ||
          (widget.initial!.lat == 0 && widget.initial!.lng == 0)
      ? null
      : LatLng(widget.initial!.lat, widget.initial!.lng);

  bool _submitted = false;
  bool _saving = false;
  bool _geocoding = false;

  static DateTime _defaultStart() {
    final n = DateTime.now();
    return DateTime(n.year, n.month, n.day + 1, 21);
  }

  @override
  void dispose() {
    for (final c in [_title, _description, _venue, _address, _image, _ticket, _tags]) {
      c.dispose();
    }
    super.dispose();
  }

  void _snack(String msg) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));

  Future<DateTime?> _pickDateTime(DateTime initial) async {
    final d = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(2020),
      lastDate: DateTime(2100),
    );
    if (d == null || !mounted) return null;
    final t = await showTimePicker(
        context: context, initialTime: TimeOfDay.fromDateTime(initial));
    if (t == null) return null;
    return DateTime(d.year, d.month, d.day, t.hour, t.minute);
  }

  Future<void> _pickStart() async {
    final v = await _pickDateTime(_start);
    if (v == null) return;
    // Sposta anche la fine mantenendo la durata.
    setState(() {
      _end = v.add(_end.difference(_start));
      _start = v;
    });
  }

  Future<void> _pickEnd() async {
    final v = await _pickDateTime(_end);
    if (v != null) setState(() => _end = v);
  }

  Future<void> _findCoords() async {
    final q = _address.text.trim();
    if (q.isEmpty) return _snack('Scrivi prima l\'indirizzo');
    setState(() => _geocoding = true);
    try {
      final p = await ref.read(geocoderProvider).geocode(q);
      if (!mounted) return;
      if (p == null) {
        _snack('Indirizzo non trovato: aggiungi il comune o tocca la mappa');
      } else {
        setState(() => _pin = p);
        _map.move(p, 16);
        _snack('Posizione trovata: controlla il pin sulla mappa');
      }
    } catch (e) {
      if (mounted) _snack('Geocoding non riuscito: $e');
    } finally {
      if (mounted) setState(() => _geocoding = false);
    }
  }

  Future<void> _save() async {
    setState(() => _submitted = true);
    final formOk = _formKey.currentState!.validate();
    if (!formOk ||
        validateRange(_start, _end) != null ||
        validateCoords(_pin?.latitude, _pin?.longitude) != null) {
      return _snack('Controlla i campi evidenziati');
    }
    final i = widget.initial;
    final now = DateTime.now();
    final event = Event(
      id: i?.id ?? '',
      title: _title.text.trim(),
      shortDescription: _description.text.trim(),
      category: _category,
      priceType: _price,
      startTime: _start,
      endTime: _end,
      venueName: _venue.text.trim(),
      address: _address.text.trim(),
      lat: _pin!.latitude,
      lng: _pin!.longitude,
      imageUrl: _image.text.trim(),
      ticketUrl: _ticket.text.trim(),
      tags: [...parseTags(_tags.text).where((t) => t != 'kids'), if (_kids) 'kids'],
      // Un evento importato modificato a mano diventa manuale: l'importer non lo sovrascrive.
      source: 'manual',
      sourceUrl: i?.sourceUrl ?? '',
      createdAt: i?.createdAt ?? now,
      updatedAt: now,
    );
    setState(() => _saving = true);
    try {
      await ref.read(adminRepositoryProvider).save(event);
      if (!mounted) return;
      _snack(i == null ? 'Evento creato' : 'Modifiche salvate');
      context.canPop() ? context.pop() : context.go('/admin');
    } catch (e) {
      if (mounted) _snack('Salvataggio non riuscito: $e');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final rangeError = _submitted ? validateRange(_start, _end) : null;
    final coordsError =
        _submitted ? validateCoords(_pin?.latitude, _pin?.longitude) : null;
    final fmt = DateFormat('EEE d MMM y · HH:mm', 'it_IT');

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.initial == null ? 'Nuovo evento' : 'Modifica evento'),
      ),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
          child: FilledButton.icon(
            style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
            onPressed: _saving ? null : _save,
            icon: _saving
                ? const SizedBox.square(
                    dimension: 18,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.check_rounded),
            label: const Text('Salva evento'),
          ),
        ),
      ),
      body: Form(
        key: _formKey,
        autovalidateMode: _submitted
            ? AutovalidateMode.onUserInteraction
            : AutovalidateMode.disabled,
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 720),
            child: ListView(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
              children: [
                if (widget.initial?.source == 'scraper')
                  Card(
                    color: t.colorScheme.tertiaryContainer,
                    child: const ListTile(
                      leading: Icon(Icons.info_outline_rounded),
                      title: Text('Evento importato automaticamente'),
                      subtitle: Text(
                          'Salvando diventa manuale e l\'importer non lo aggiornerà più.'),
                    ),
                  ),
                const _Section('Informazioni'),
                TextFormField(
                  controller: _title,
                  textCapitalization: TextCapitalization.sentences,
                  decoration: const InputDecoration(labelText: 'Titolo *'),
                  validator: (v) => validateRequired(v, max: 120),
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _description,
                  maxLines: 3,
                  minLines: 2,
                  textCapitalization: TextCapitalization.sentences,
                  decoration: const InputDecoration(
                      labelText: 'Descrizione breve *', alignLabelWithHint: true),
                  validator: (v) => validateRequired(v, max: 300),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  initialValue: categories.containsKey(_category) ? _category : 'other',
                  decoration: const InputDecoration(labelText: 'Categoria'),
                  items: [
                    for (final c in categories.entries)
                      DropdownMenuItem(
                        value: c.key,
                        child: Row(children: [
                          Icon(c.value.icon, size: 20, color: c.value.color),
                          const SizedBox(width: 12),
                          Text(c.value.label),
                        ]),
                      ),
                  ],
                  onChanged: (v) => setState(() => _category = v ?? 'other'),
                ),
                const SizedBox(height: 16),
                Text('Prezzo', style: t.textTheme.labelLarge),
                const SizedBox(height: 8),
                SegmentedButton<String>(
                  segments: [
                    for (final p in const ['free', 'low', 'premium'])
                      ButtonSegment(value: p, label: Text(priceLabel(p))),
                  ],
                  selected: {_price},
                  onSelectionChanged: (s) => setState(() => _price = s.first),
                ),
                const SizedBox(height: 8),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Adatto ai bambini'),
                  value: _kids,
                  onChanged: (v) => setState(() => _kids = v),
                ),
                const _Section('Quando'),
                _DateTile(
                    label: 'Inizio', value: fmt.format(_start), onTap: _pickStart),
                _DateTile(
                    label: 'Fine',
                    value: fmt.format(_end),
                    onTap: _pickEnd,
                    error: rangeError),
                const _Section('Dove'),
                TextFormField(
                  controller: _venue,
                  decoration: const InputDecoration(labelText: 'Nome luogo *'),
                  validator: (v) => validateRequired(v, max: 120),
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _address,
                  decoration: const InputDecoration(
                      labelText: 'Indirizzo *', hintText: 'Via, civico, comune'),
                  validator: (v) => validateRequired(v, max: 200),
                ),
                const SizedBox(height: 12),
                Align(
                  alignment: Alignment.centerLeft,
                  child: FilledButton.tonalIcon(
                    onPressed: _geocoding ? null : _findCoords,
                    icon: _geocoding
                        ? const SizedBox.square(
                            dimension: 18,
                            child: CircularProgressIndicator(strokeWidth: 2))
                        : const Icon(Icons.travel_explore_rounded),
                    label: const Text('Trova coordinate'),
                  ),
                ),
                const SizedBox(height: 12),
                ClipRRect(
                  borderRadius: BorderRadius.circular(20),
                  child: SizedBox(
                    height: 240,
                    child: FlutterMap(
                      mapController: _map,
                      options: MapOptions(
                        initialCenter: _pin ?? modenaCenter,
                        initialZoom: _pin == null ? 12 : 16,
                        onTap: (_, p) => setState(() => _pin = p),
                      ),
                      children: [
                        TileLayer(
                          urlTemplate:
                              'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                          userAgentPackageName: 'com.example.app_eventi',
                          maxNativeZoom: 19,
                        ),
                        if (_pin != null)
                          MarkerLayer(markers: [
                            Marker(
                              point: _pin!,
                              width: 40,
                              height: 40,
                              alignment: Alignment.topCenter,
                              child: Icon(Icons.location_on,
                                  size: 40, color: t.colorScheme.primary),
                            ),
                          ]),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  coordsError ??
                      (_pin == null
                          ? 'Tocca la mappa per posizionare il pin a mano.'
                          : 'Pin: ${_pin!.latitude.toStringAsFixed(5)}, '
                              '${_pin!.longitude.toStringAsFixed(5)} · tocca per spostarlo'),
                  style: t.textTheme.bodySmall?.copyWith(
                      color: coordsError != null
                          ? t.colorScheme.error
                          : t.colorScheme.onSurfaceVariant),
                ),
                const _Section('Link e tag'),
                TextFormField(
                  controller: _image,
                  keyboardType: TextInputType.url,
                  decoration: const InputDecoration(labelText: 'URL immagine'),
                  validator: validateOptionalUrl,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _ticket,
                  keyboardType: TextInputType.url,
                  decoration: const InputDecoration(labelText: 'URL biglietti'),
                  validator: validateOptionalUrl,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _tags,
                  decoration: const InputDecoration(
                      labelText: 'Tag', hintText: 'outdoor, live, family'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Section extends StatelessWidget {
  final String title;
  const _Section(this.title);

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 24, 4, 12),
      child: Text(title.toUpperCase(),
          style: t.textTheme.labelSmall?.copyWith(color: t.colorScheme.primary)),
    );
  }
}

class _DateTile extends StatelessWidget {
  final String label;
  final String value;
  final VoidCallback onTap;
  final String? error;
  const _DateTile(
      {required this.label, required this.value, required this.onTap, this.error});

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 4),
      leading: const Icon(Icons.schedule_rounded),
      title: Text(label),
      subtitle: Text(error == null ? value : '$value · $error',
          style: error != null ? TextStyle(color: t.colorScheme.error) : null),
      trailing: const Icon(Icons.edit_calendar_rounded),
      onTap: onTap,
    );
  }
}

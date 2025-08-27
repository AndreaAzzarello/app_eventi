import 'package:shared_preferences/shared_preferences.dart';

class FavoritesStore {
  static const _k = 'fav_event_ids';

  Future<Set<String>> _get() async {
    final sp = await SharedPreferences.getInstance();
    return sp.getStringList(_k)?.toSet() ?? <String>{};
  }

  Future<bool> isFav(String id) async => (await _get()).contains(id);

  Future<void> toggle(String id) async {
    final sp = await SharedPreferences.getInstance();
    final cur = await _get();
    if (cur.contains(id)) {
      cur.remove(id);
    } else {
      cur.add(id);
    }
    await sp.setStringList(_k, cur.toList());
  }
}

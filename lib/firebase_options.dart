// Segnaposto scritto a mano con i valori Android presi da
// android/app/google-services.json.
// Rigeneralo con `flutterfire configure` per abilitare web e iOS:
// il comando sovrascrive questo file con la configurazione completa.
import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'package:flutter/foundation.dart'
    show defaultTargetPlatform, kIsWeb, TargetPlatform;

class DefaultFirebaseOptions {
  static FirebaseOptions get currentPlatform {
    if (kIsWeb) return _notConfigured('web');
    return switch (defaultTargetPlatform) {
      TargetPlatform.android => android,
      _ => _notConfigured(defaultTargetPlatform.name),
    };
  }

  static const FirebaseOptions android = FirebaseOptions(
    apiKey: 'AIzaSyB8zfwusSjZcToqdkSn8-5fDoba9F8R7UM',
    appId: '1:398100140878:android:ba798056734a7afe6f441f',
    messagingSenderId: '398100140878',
    projectId: 'appeventi-1e860',
    storageBucket: 'appeventi-1e860.firebasestorage.app',
  );

  static Never _notConfigured(String platform) => throw UnsupportedError(
        'Firebase non è configurato per "$platform". '
        'Esegui `flutterfire configure` per rigenerare lib/firebase_options.dart.',
      );
}

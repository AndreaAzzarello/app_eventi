import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Deve coincidere con l'email in firestore.rules: le regole sono il vero controllo,
/// questo serve solo a mostrare la UI giusta.
const adminEmail = 'azzatubo@gmail.com';

class AuthState {
  final String? email;
  final bool isAdmin;
  const AuthState({this.email, this.isAdmin = false});
  bool get signedIn => email != null;
}

final authStateProvider = StreamProvider<AuthState>((ref) {
  if (Firebase.apps.isEmpty) {
    throw StateError('Firebase non è configurato per questa piattaforma.');
  }
  return FirebaseAuth.instance.authStateChanges().map((u) => AuthState(
        email: u?.email,
        isAdmin: u != null && u.email == adminEmail && u.emailVerified,
      ));
});

Future<void> signInWithGoogle() async {
  final provider = GoogleAuthProvider()..setCustomParameters({'prompt': 'select_account'});
  if (kIsWeb) {
    await FirebaseAuth.instance.signInWithPopup(provider);
  } else {
    await FirebaseAuth.instance.signInWithProvider(provider);
  }
}

Future<void> signOut() => FirebaseAuth.instance.signOut();

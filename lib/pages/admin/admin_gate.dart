import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/auth.dart';
import '../../widgets/state_views.dart';

/// Mostra [child] solo all'admin; altrimenti login o "non autorizzato".
class AdminGate extends ConsumerWidget {
  final Widget child;
  const AdminGate({super.key, required this.child});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authStateProvider);
    final Widget body = auth.when(
      loading: () => const LoadingView(),
      error: (e, _) => MessageView(
        icon: Icons.cloud_off_rounded,
        title: 'Accesso non disponibile',
        message: e is StateError ? e.message : '$e',
      ),
      data: (a) => a.isAdmin
          ? child
          : a.signedIn
              ? MessageView(
                  icon: Icons.block_rounded,
                  title: 'Account non autorizzato',
                  message: '${a.email} non ha accesso all\'area admin.',
                  action: FilledButton.tonal(
                      onPressed: signOut, child: const Text('Cambia account')),
                )
              : const _SignInView(),
    );
    if (auth.value?.isAdmin ?? false) return body;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Area admin'),
        leading: IconButton(
          tooltip: 'Torna agli eventi',
          onPressed: () => context.go('/'),
          icon: const Icon(Icons.arrow_back_rounded),
        ),
      ),
      body: body,
    );
  }
}

class _SignInView extends StatefulWidget {
  const _SignInView();

  @override
  State<_SignInView> createState() => _SignInViewState();
}

class _SignInViewState extends State<_SignInView> {
  bool _busy = false;

  Future<void> _signIn() async {
    setState(() => _busy = true);
    try {
      await signInWithGoogle();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Accesso non riuscito: $e')));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => MessageView(
        icon: Icons.lock_outline_rounded,
        title: 'Area riservata',
        message: 'Accedi con l\'account Google dell\'amministratore.',
        action: FilledButton.icon(
          onPressed: _busy ? null : _signIn,
          icon: _busy
              ? const SizedBox.square(
                  dimension: 18,
                  child: CircularProgressIndicator(strokeWidth: 2))
              : const Icon(Icons.login_rounded),
          label: const Text('Accedi con Google'),
        ),
      );
}

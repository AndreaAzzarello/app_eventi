import 'package:flutter/material.dart';

class LoadingView extends StatelessWidget {
  const LoadingView({super.key});

  @override
  Widget build(BuildContext context) =>
      const Center(child: CircularProgressIndicator());
}

/// Messaggio centrato per errore e lista vuota, con azione opzionale.
class MessageView extends StatelessWidget {
  final IconData icon;
  final String title;
  final String? message;
  final Widget? action;

  const MessageView({
    super.key,
    required this.icon,
    required this.title,
    this.message,
    this.action,
  });

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(32),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 360),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              CircleAvatar(
                radius: 36,
                backgroundColor: t.colorScheme.secondaryContainer,
                child: Icon(icon,
                    size: 32, color: t.colorScheme.onSecondaryContainer),
              ),
              const SizedBox(height: 20),
              Text(title,
                  textAlign: TextAlign.center, style: t.textTheme.titleLarge),
              if (message != null) ...[
                const SizedBox(height: 8),
                Text(message!,
                    textAlign: TextAlign.center,
                    style: t.textTheme.bodyMedium
                        ?.copyWith(color: t.colorScheme.onSurfaceVariant)),
              ],
              if (action != null) ...[const SizedBox(height: 20), action!],
            ],
          ),
        ),
      ),
    );
  }
}

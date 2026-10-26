import 'package:flutter/material.dart';

/// Terracotta dei tetti di Modena: è il seed di tutta la palette.
const brandSeed = Color(0xFFB8432F);

ThemeData buildTheme(Brightness brightness) {
  final scheme = ColorScheme.fromSeed(
    seedColor: brandSeed,
    brightness: brightness,
    dynamicSchemeVariant: DynamicSchemeVariant.fidelity,
  );
  final base = ThemeData(colorScheme: scheme, useMaterial3: true);
  final text = base.textTheme;
  return base.copyWith(
    scaffoldBackgroundColor: scheme.surface,
    textTheme: text.copyWith(
      headlineMedium: text.headlineMedium
          ?.copyWith(fontWeight: FontWeight.w800, letterSpacing: -0.8),
      headlineSmall: text.headlineSmall
          ?.copyWith(fontWeight: FontWeight.w800, letterSpacing: -0.5),
      titleLarge: text.titleLarge
          ?.copyWith(fontWeight: FontWeight.w700, letterSpacing: -0.3),
      titleMedium: text.titleMedium
          ?.copyWith(fontWeight: FontWeight.w700, letterSpacing: -0.1),
      labelSmall: text.labelSmall
          ?.copyWith(fontWeight: FontWeight.w700, letterSpacing: 0.8),
    ),
    appBarTheme: AppBarTheme(
      backgroundColor: scheme.surface,
      surfaceTintColor: Colors.transparent,
      titleTextStyle: text.titleLarge?.copyWith(
          fontWeight: FontWeight.w800,
          letterSpacing: -0.5,
          color: scheme.onSurface),
    ),
    cardTheme: CardThemeData(
      elevation: 0,
      margin: EdgeInsets.zero,
      color: scheme.surfaceContainerLow,
      clipBehavior: Clip.antiAlias,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: BorderSide(color: scheme.outlineVariant.withValues(alpha: 0.5)),
      ),
    ),
    chipTheme: base.chipTheme.copyWith(
      shape: const StadiumBorder(),
      side: BorderSide(color: scheme.outlineVariant),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: scheme.surfaceContainerHigh,
      isDense: true,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(28),
        borderSide: BorderSide.none,
      ),
    ),
  );
}

/// Etichetta, icona e colore di ogni categoria (Event.category).
class CategoryStyle {
  final String label;
  final IconData icon;
  final Color color;
  const CategoryStyle(this.label, this.icon, this.color);
}

const categories = <String, CategoryStyle>{
  'music': CategoryStyle('Musica', Icons.music_note_rounded, Color(0xFF7C4DFF)),
  'food': CategoryStyle('Cibo', Icons.restaurant_rounded, Color(0xFFE65100)),
  'culture': CategoryStyle('Cultura', Icons.palette_rounded, Color(0xFF00897B)),
  'sport': CategoryStyle('Sport', Icons.directions_run_rounded, Color(0xFF1E88E5)),
  'kids': CategoryStyle('Bambini', Icons.child_care_rounded, Color(0xFFD81B60)),
  'market': CategoryStyle('Mercatini', Icons.storefront_rounded, Color(0xFF6D4C41)),
  'other': CategoryStyle('Altro', Icons.event_rounded, Color(0xFF546E7A)),
};

CategoryStyle categoryStyle(String category) =>
    categories[category] ?? categories['other']!;

import 'package:flutter/material.dart';

/// Central theme for the VoiceBook app.
/// Warm, high-contrast palette chosen for readability by users who may
/// glance at the screen quickly rather than read closely.
class AppTheme {
  static const Color primary = Color(0xFFB8452B); // terracotta / tent-cloth red
  static const Color primaryDark = Color(0xFF8C3320);
  static const Color accent = Color(0xFFE0A030); // marigold gold
  static const Color success = Color(0xFF2E7D4F);
  static const Color danger = Color(0xFFC0392B);
  static const Color surface = Color(0xFFFFF8F0);
  static const Color textDark = Color(0xFF2B2320);
  static const Color textMuted = Color(0xFF6B5F58);

  static ThemeData get theme {
    return ThemeData(
      useMaterial3: true,
      scaffoldBackgroundColor: surface,
      colorScheme: ColorScheme.fromSeed(
        seedColor: primary,
        primary: primary,
        secondary: accent,
        surface: surface,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: primary,
        foregroundColor: Colors.white,
        elevation: 0,
        centerTitle: true,
      ),
      textTheme: const TextTheme(
        headlineMedium: TextStyle(fontWeight: FontWeight.bold, color: textDark),
        titleLarge: TextStyle(fontWeight: FontWeight.w600, color: textDark),
        bodyLarge: TextStyle(fontSize: 16, color: textDark),
        bodyMedium: TextStyle(fontSize: 14, color: textMuted),
      ),
      cardTheme: CardThemeData(
        elevation: 1,
        color: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        margin: const EdgeInsets.symmetric(vertical: 6, horizontal: 0),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primary,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 24),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide.none,
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      ),
    );
  }
}

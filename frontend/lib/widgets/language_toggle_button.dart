import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/locale_provider.dart';

/// Small pill button for the top-right of every app bar. Tapping it flips
/// the whole app's text between English and Kannada instantly.
class LanguageToggleButton extends StatelessWidget {
  const LanguageToggleButton({super.key});

  @override
  Widget build(BuildContext context) {
    final localeProvider = context.watch<LocaleProvider>();
    final isKannada = localeProvider.isKannada;

    return Padding(
      padding: const EdgeInsets.only(right: 12),
      child: Center(
        child: Material(
          color: Colors.white.withOpacity(0.18),
          borderRadius: BorderRadius.circular(20),
          child: InkWell(
            borderRadius: BorderRadius.circular(20),
            onTap: () => context.read<LocaleProvider>().toggle(),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.translate_rounded, size: 16, color: Colors.white),
                  const SizedBox(width: 5),
                  Text(
                    isKannada ? 'ಕನ್ನಡ' : 'EN',
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 12.5),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

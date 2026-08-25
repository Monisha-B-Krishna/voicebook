import 'package:flutter/material.dart';

enum AppLocale { en, kn }

/// App-wide language switch. No routing/localization delegates needed —
/// screens just read `context.watch<LocaleProvider>().locale` and pick the
/// right string via the `AppStrings` lookup / `context.tr()` extension.
class LocaleProvider extends ChangeNotifier {
  AppLocale _locale = AppLocale.en;
  AppLocale get locale => _locale;
  bool get isKannada => _locale == AppLocale.kn;

  void toggle() {
    _locale = _locale == AppLocale.en ? AppLocale.kn : AppLocale.en;
    notifyListeners();
  }
}

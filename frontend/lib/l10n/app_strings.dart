import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/locale_provider.dart';

/// All user-facing text in the app, keyed by a short id, with an English
/// and Kannada value. Screens call `context.tr('key')` to get the string
/// in whichever language is currently selected - flipped instantly and
/// app-wide by the language toggle button in each screen's app bar.
///
/// IMPORTANT: `context.tr()` defaults to `listen: true` (uses
/// `context.watch`), which is REQUIRED inside build() methods so the UI
/// rebuilds when the language toggle is tapped - but `context.watch` can
/// ONLY be called during build. Calling it from a button's onPressed
/// handler or inside an async callback throws a hard Provider assertion
/// error. For those cases, call `context.tr('key', listen: false)`
/// instead, which uses `context.read` (no rebuild subscription, just
/// reads the current value once - safe to call from anywhere).
class AppStrings {
  static const Map<String, Map<AppLocale, String>> _strings = {
    'app_name': {AppLocale.en: 'VoiceBook', AppLocale.kn: 'ವಾಯ್ಸ್‌ಬುಕ್'},
    'hello': {AppLocale.en: 'Hello', AppLocale.kn: 'ನಮಸ್ಕಾರ'},

    // Home
    'todays_bookings': {AppLocale.en: "Today's Bookings", AppLocale.kn: 'ಇಂದಿನ ಬುಕಿಂಗ್‌ಗಳು'},
    'pending_balance': {AppLocale.en: 'Pending Balance', AppLocale.kn: 'ಬಾಕಿ ಮೊತ್ತ'},
    'customers': {AppLocale.en: 'Customers', AppLocale.kn: 'ಗ್ರಾಹಕರು'},
    'inventory_items': {AppLocale.en: 'Inventory Items', AppLocale.kn: 'ಸ್ಟಾಕ್ ವಸ್ತುಗಳು'},
    'types_suffix': {AppLocale.en: 'types', AppLocale.kn: 'ಬಗೆಗಳು'},
    'upcoming_bookings': {AppLocale.en: 'Upcoming Bookings', AppLocale.kn: 'ಮುಂಬರುವ ಬುಕಿಂಗ್‌ಗಳು'},
    'see_all': {AppLocale.en: 'See all', AppLocale.kn: 'ಎಲ್ಲಾ ನೋಡಿ'},
    'no_upcoming_bookings': {
      AppLocale.en: 'No upcoming bookings yet. Try speaking one!',
      AppLocale.kn: 'ಇನ್ನೂ ಯಾವುದೇ ಬುಕಿಂಗ್ ಇಲ್ಲ. ಮಾತನಾಡಿ ನೋಡಿ!'
    },
    'could_not_start_recording': {
      AppLocale.en: 'Could not start recording',
      AppLocale.kn: 'ರೆಕಾರ್ಡಿಂಗ್ ಪ್ರಾರಂಭಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ'
    },
    'saved_successfully': {AppLocale.en: 'Saved successfully', AppLocale.kn: 'ಯಶಸ್ವಿಯಾಗಿ ಉಳಿಸಲಾಗಿದೆ'},

    // Mic button
    'mic_understanding': {AppLocale.en: 'Understanding...', AppLocale.kn: 'ಅರ್ಥಮಾಡಿಕೊಳ್ಳುತ್ತಿದೆ...'},
    'mic_listening': {AppLocale.en: 'Listening... tap to stop', AppLocale.kn: 'ಕೇಳುತ್ತಿದೆ... ನಿಲ್ಲಿಸಲು ಟ್ಯಾಪ್ ಮಾಡಿ'},
    'mic_idle': {
      AppLocale.en: 'Hold or tap to speak',
      AppLocale.kn: 'ಮಾತನಾಡಲು ಒತ್ತಿ ಹಿಡಿಯಿರಿ ಅಥವಾ ಟ್ಯಾಪ್ ಮಾಡಿ'
    },

    // Bookings screen
    'bookings': {AppLocale.en: 'Bookings', AppLocale.kn: 'ಬುಕಿಂಗ್‌ಗಳು'},
    'search_customer_name': {
      AppLocale.en: 'Search by customer name...',
      AppLocale.kn: 'ಗ್ರಾಹಕರ ಹೆಸರಿನಿಂದ ಹುಡುಕಿ...'
    },
    'filter_all': {AppLocale.en: 'All', AppLocale.kn: 'ಎಲ್ಲಾ'},
    'filter_upcoming': {AppLocale.en: 'Upcoming', AppLocale.kn: 'ಮುಂಬರುವ'},
    'filter_completed': {AppLocale.en: 'Completed', AppLocale.kn: 'ಮುಗಿದಿದೆ'},
    'filter_cancelled': {AppLocale.en: 'Cancelled', AppLocale.kn: 'ರದ್ದಾಗಿದೆ'},
    'no_bookings_found': {AppLocale.en: 'No bookings found', AppLocale.kn: 'ಯಾವುದೇ ಬುಕಿಂಗ್ ಸಿಗಲಿಲ್ಲ'},
    'total_amount': {AppLocale.en: 'Total Amount', AppLocale.kn: 'ಒಟ್ಟು ಮೊತ್ತ'},
    'advance_paid': {AppLocale.en: 'Advance Paid', AppLocale.kn: 'ಪಾವತಿಸಿದ ಅಡ್ವಾನ್ಸ್'},
    'balance_due': {AppLocale.en: 'Balance Due', AppLocale.kn: 'ಬಾಕಿ ಮೊತ್ತ'},
    'returned': {AppLocale.en: 'Returned', AppLocale.kn: 'ಹಿಂತಿರುಗಿಸಲಾಗಿದೆ'},
    'yes': {AppLocale.en: 'Yes', AppLocale.kn: 'ಹೌದು'},
    'no': {AppLocale.en: 'No', AppLocale.kn: 'ಇಲ್ಲ'},
    'paid': {AppLocale.en: 'Paid', AppLocale.kn: 'ಪಾವತಿಸಲಾಗಿದೆ'},
    'due': {AppLocale.en: 'due', AppLocale.kn: 'ಬಾಕಿ'},

    // Customers screen
    'search_name_nickname': {
      AppLocale.en: 'Search name or nickname...',
      AppLocale.kn: 'ಹೆಸರು ಅಥವಾ ಅಡ್ಡಹೆಸರು ಹುಡುಕಿ...'
    },
    'no_customers_found': {AppLocale.en: 'No customers found', AppLocale.kn: 'ಯಾವುದೇ ಗ್ರಾಹಕರು ಸಿಗಲಿಲ್ಲ'},
    'aka': {AppLocale.en: 'aka', AppLocale.kn: 'ಅಡ್ಡಹೆಸರು'},

    // Inventory screen
    'inventory': {AppLocale.en: 'Inventory', AppLocale.kn: 'ಸ್ಟಾಕ್'},
    'low_stock': {AppLocale.en: 'Low stock', AppLocale.kn: 'ಕಡಿಮೆ ಸ್ಟಾಕ್'},
    'booked_colon': {AppLocale.en: 'Booked', AppLocale.kn: 'ಬುಕ್ ಆಗಿದೆ'},
    'available_colon': {AppLocale.en: 'Available', AppLocale.kn: 'ಲಭ್ಯವಿದೆ'},
    'total_colon': {AppLocale.en: 'Total', AppLocale.kn: 'ಒಟ್ಟು'},

    // Reports screen
    'reports': {AppLocale.en: 'Reports', AppLocale.kn: 'ವರದಿಗಳು'},
    'total_revenue': {AppLocale.en: 'Total Revenue', AppLocale.kn: 'ಒಟ್ಟು ಆದಾಯ'},
    'todays_events': {AppLocale.en: "Today's Events", AppLocale.kn: 'ಇಂದಿನ ಕಾರ್ಯಕ್ರಮಗಳು'},
    'monthly_income': {AppLocale.en: 'Monthly Income', AppLocale.kn: 'ಮಾಸಿಕ ಆದಾಯ'},
    'recent_payments': {AppLocale.en: 'Recent Payments', AppLocale.kn: 'ಇತ್ತೀಚಿನ ಪಾವತಿಗಳು'},
    'no_payments_yet': {
      AppLocale.en: 'No payments recorded yet.',
      AppLocale.kn: 'ಇನ್ನೂ ಯಾವುದೇ ಪಾವತಿ ದಾಖಲಾಗಿಲ್ಲ.'
    },
    'payment_received': {AppLocale.en: 'Payment received', AppLocale.kn: 'ಪಾವತಿ ಸ್ವೀಕರಿಸಲಾಗಿದೆ'},

    // Voice confirm sheet
    'title_new_booking': {AppLocale.en: 'New Booking', AppLocale.kn: 'ಹೊಸ ಬುಕಿಂಗ್'},
    'title_payment_received': {AppLocale.en: 'Payment Received', AppLocale.kn: 'ಪಾವತಿ ಸ್ವೀಕರಿಸಲಾಗಿದೆ'},
    'title_items_returned': {AppLocale.en: 'Items Returned', AppLocale.kn: 'ವಸ್ತುಗಳು ಹಿಂತಿರುಗಿದೆ'},
    'title_answer': {AppLocale.en: 'Answer', AppLocale.kn: 'ಉತ್ತರ'},
    'title_not_understood': {AppLocale.en: 'Not Understood', AppLocale.kn: 'ಅರ್ಥವಾಗಲಿಲ್ಲ'},
    'label_customer': {AppLocale.en: 'Customer', AppLocale.kn: 'ಗ್ರಾಹಕ'},
    'label_date': {AppLocale.en: 'Date', AppLocale.kn: 'ದಿನಾಂಕ'},
    'label_items': {AppLocale.en: 'Items', AppLocale.kn: 'ವಸ್ತುಗಳು'},
    'label_advance': {AppLocale.en: 'Advance', AppLocale.kn: 'ಅಡ್ವಾನ್ಸ್'},
    'btn_no_discard': {AppLocale.en: 'No, discard', AppLocale.kn: 'ಬೇಡ, ಅಳಿಸಿ'},
    'btn_yes_save': {AppLocale.en: 'Yes, save', AppLocale.kn: 'ಹೌದು, ಉಳಿಸಿ'},
    'btn_save_anyway': {AppLocale.en: 'Save anyway', AppLocale.kn: 'ಆದರೂ ಉಳಿಸಿ'},
    'btn_close': {AppLocale.en: 'Close', AppLocale.kn: 'ಮುಚ್ಚಿ'},
    'not_understood_fallback': {
      AppLocale.en: "Sorry, I couldn't understand that. Please try again.",
      AppLocale.kn: 'ಕ್ಷಮಿಸಿ, ಅರ್ಥವಾಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.'
    },
  };

  static String of(BuildContext context, String key, {bool listen = true}) {
    final locale = listen
        ? context.watch<LocaleProvider>().locale
        : context.read<LocaleProvider>().locale;
    return _strings[key]?[locale] ?? key;
  }
}

extension TrContext on BuildContext {
  /// [listen] defaults to true (safe and correct inside build() methods,
  /// where the UI needs to rebuild on language toggle). Pass
  /// `listen: false` when calling from a button handler, async callback,
  /// or anywhere NOT during build - otherwise this throws a Provider
  /// assertion error.
  String tr(String key, {bool listen = true}) => AppStrings.of(this, key, listen: listen);
}

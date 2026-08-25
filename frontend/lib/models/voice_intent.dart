/// The structured result that comes back from the backend after
/// ASR (Sarvam) -> NLU (Claude) processing of the owner's spoken audio.
///
/// In production this is parsed from the JSON the FastAPI backend returns,
/// e.g.:
/// {
///   "intent": "booking",
///   "customer": "Raju",
///   "date": "2026-06-15",
///   "items": [{"name": "Chair", "qty": 50}],
///   "advance": 2000,
///   "spoken_text": "Raju ge June 15 ge 50 chairs booking, 2000 advance",
///   "confidence": 0.91
/// }
enum VoiceIntentType { booking, payment, returnItem, query, unknown }

class VoiceIntent {
  final VoiceIntentType type;
  final String? customerName;
  final DateTime? eventDate;
  final List<Map<String, dynamic>> items; // [{name, qty}]
  final double? advance;
  final String spokenText;
  final double confidence;
  final String? answerText; // for query intents, the spoken-back answer

  VoiceIntent({
    required this.type,
    required this.spokenText,
    this.customerName,
    this.eventDate,
    this.items = const [],
    this.advance,
    this.confidence = 1.0,
    this.answerText,
  });

  factory VoiceIntent.fromJson(Map<String, dynamic> json) {
    VoiceIntentType t;
    switch (json['intent']) {
      case 'booking':
        t = VoiceIntentType.booking;
        break;
      case 'payment':
        t = VoiceIntentType.payment;
        break;
      case 'return':
        t = VoiceIntentType.returnItem;
        break;
      case 'query':
        t = VoiceIntentType.query;
        break;
      default:
        t = VoiceIntentType.unknown;
    }
    return VoiceIntent(
      type: t,
      customerName: json['customer'] as String?,
      eventDate: json['date'] != null ? DateTime.tryParse(json['date']) : null,
      items: (json['items'] as List?)?.cast<Map<String, dynamic>>() ?? [],
      advance: (json['advance'] as num?)?.toDouble(),
      spokenText: json['spoken_text'] as String? ?? '',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 1.0,
      answerText: json['answer_text'] as String?,
    );
  }
}

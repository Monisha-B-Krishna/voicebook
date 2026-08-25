import '../models/voice_intent.dart';

/// Stands in for the real Sarvam ASR + Claude NLU backend call while the
/// backend (Phases 8-10 of the project plan) isn't deployed yet.
///
/// This lets the Flutter app be fully demoed end-to-end (mic -> parsed
/// intent -> confirmation -> save) without any server running. Swap this
/// out for real ApiService calls once the backend is live — no screen code
/// needs to change since both return the same VoiceIntent model.
class MockNluService {
  static VoiceIntent mockFromRecording(int audioSizeBytes) {
    // Rotate through a few representative example utterances from the
    // abstract so reviewers/testers see different flows each time.
    final samples = [
      'Raju ge June 15 ge 50 pathre booking maadidaare, 2000 advance kottidaare',
      'Suresh estu baaki haakidaane?',
      'Manju return maadidru 20 chairs',
      'Ganesh ge next Sunday 100 vessels, 5000 advance',
    ];
    final index = audioSizeBytes % samples.length;
    return mockFromText(samples[index]);
  }

  static VoiceIntent mockFromText(String text) {
    final lower = text.toLowerCase();

    if (lower.contains('baaki') || lower.contains('balance') || lower.contains('estu')) {
      final name = _extractName(text) ?? 'Customer';
      return VoiceIntent(
        type: VoiceIntentType.query,
        spokenText: text,
        customerName: name,
        answerText: '$name has a pending balance of ₹4,500',
        confidence: 0.9,
      );
    }

    if (lower.contains('return')) {
      return VoiceIntent(
        type: VoiceIntentType.returnItem,
        spokenText: text,
        customerName: _extractName(text) ?? 'Customer',
        items: [
          {'name': 'Chairs', 'qty': 20}
        ],
        confidence: 0.85,
      );
    }

    if (lower.contains('booking') || lower.contains('vessel') || lower.contains('pathre') || lower.contains('chair')) {
      return VoiceIntent(
        type: VoiceIntentType.booking,
        spokenText: text,
        customerName: _extractName(text) ?? 'New Customer',
        eventDate: DateTime.now().add(const Duration(days: 14)),
        items: [
          {'name': lower.contains('chair') ? 'Chairs' : 'Vessels', 'qty': lower.contains('100') ? 100 : 50}
        ],
        advance: lower.contains('5000') ? 5000 : 2000,
        confidence: 0.88,
      );
    }

    return VoiceIntent(
      type: VoiceIntentType.unknown,
      spokenText: text,
      confidence: 0.4,
      answerText: "Sorry, I didn't understand that. Please try again.",
    );
  }

  static String? _extractName(String text) {
    // Extremely naive heuristic for the mock — real extraction happens via
    // the Claude NLU prompt on the backend (see Phase 10 of the plan).
    final knownNames = ['Raju', 'Suresh', 'Manju', 'Ganesh'];
    for (final n in knownNames) {
      if (text.toLowerCase().contains(n.toLowerCase())) return n;
    }
    return null;
  }
}

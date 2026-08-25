/// Matches the REAL backend contract: shared/schemas/nlu_schema.py's
/// NLUResult and Transaction Pydantic models.
///
/// IMPORTANT DIFFERENCE from the old VoiceIntent model this replaces:
/// one utterance can produce MULTIPLE transactions (a multi-item booking,
/// or a booking + payment together, or even bookings for two different
/// customers in one sentence - all of these are real, tested cases in
/// the actual NLU pipeline). The UI must show a LIST, not assume one.

enum TransactionIntent { booking, payment, returnItem, query, unknown }

TransactionIntent _intentFromString(String? value) {
  switch (value) {
    case 'BOOKING':
      return TransactionIntent.booking;
    case 'PAYMENT':
      return TransactionIntent.payment;
    case 'RETURN':
      return TransactionIntent.returnItem;
    case 'QUERY':
      return TransactionIntent.query;
    default:
      return TransactionIntent.unknown;
  }
}

/// One structured transaction - matches Python's Transaction model exactly,
/// field-for-field (snake_case JSON keys, same as the Pydantic model uses).
class VoiceTransaction {
  final TransactionIntent intent;
  final String? customerName;
  final String? date; // ISO date string "YYYY-MM-DD", or null
  final String? item;
  final int? quantity;
  final double? amount;
  final String? paymentType;

  VoiceTransaction({
    required this.intent,
    this.customerName,
    this.date,
    this.item,
    this.quantity,
    this.amount,
    this.paymentType,
  });

  factory VoiceTransaction.fromJson(Map<String, dynamic> json) {
    return VoiceTransaction(
      intent: _intentFromString(json['intent'] as String?),
      customerName: json['customer_name'] as String?,
      date: json['date'] as String?,
      item: json['item'] as String?,
      quantity: json['quantity'] as int?,
      amount: (json['amount'] as num?)?.toDouble(),
      paymentType: json['payment_type'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'intent': intent == TransactionIntent.booking
            ? 'BOOKING'
            : intent == TransactionIntent.payment
                ? 'PAYMENT'
                : intent == TransactionIntent.returnItem
                    ? 'RETURN'
                    : intent == TransactionIntent.query
                        ? 'QUERY'
                        : 'UNKNOWN',
        'customer_name': customerName,
        'date': date,
        'item': item,
        'quantity': quantity,
        'amount': amount,
        'payment_type': paymentType,
      };

  /// Returns a copy with fields overridden - used when the owner EDITS a
  /// transaction on the confirmation screen before saving (e.g. correcting
  /// a misheard item name or quantity).
  VoiceTransaction copyWith({
    TransactionIntent? intent,
    String? customerName,
    String? date,
    String? item,
    int? quantity,
    double? amount,
    String? paymentType,
  }) {
    return VoiceTransaction(
      intent: intent ?? this.intent,
      customerName: customerName ?? this.customerName,
      date: date ?? this.date,
      item: item ?? this.item,
      quantity: quantity ?? this.quantity,
      amount: amount ?? this.amount,
      paymentType: paymentType ?? this.paymentType,
    );
  }
}

/// The full parsed result of one utterance - matches Python's NLUResult
/// exactly. This is what /voice/process-audio returns, and (after the
/// owner reviews/edits/confirms) what gets sent back to /voice-transactions/.
class VoiceParseResult {
  final String rawTranscript;
  final String entryTimestamp;
  final List<VoiceTransaction> transactions;
  final bool isMultiIntent;
  final String? confidenceNote;

  VoiceParseResult({
    required this.rawTranscript,
    required this.entryTimestamp,
    required this.transactions,
    required this.isMultiIntent,
    this.confidenceNote,
  });

  factory VoiceParseResult.fromJson(Map<String, dynamic> json) {
    final txnList = (json['transactions'] as List?) ?? [];
    return VoiceParseResult(
      rawTranscript: json['raw_transcript'] as String? ?? '',
      entryTimestamp: json['entry_timestamp'] as String? ?? '',
      transactions: txnList
          .map((t) => VoiceTransaction.fromJson(t as Map<String, dynamic>))
          .toList(),
      isMultiIntent: json['is_multi_intent'] as bool? ?? false,
      confidenceNote: json['confidence_note'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'raw_transcript': rawTranscript,
        'entry_timestamp': entryTimestamp,
        'transactions': transactions.map((t) => t.toJson()).toList(),
        'is_multi_intent': isMultiIntent,
        'confidence_note': confidenceNote,
      };

  /// Returns a copy of this result with one transaction replaced - used
  /// when the owner edits a single line on the confirm screen.
  VoiceParseResult withTransactionAt(int index, VoiceTransaction updated) {
    final newList = List<VoiceTransaction>.from(transactions);
    newList[index] = updated;
    return VoiceParseResult(
      rawTranscript: rawTranscript,
      entryTimestamp: entryTimestamp,
      transactions: newList,
      isMultiIntent: isMultiIntent,
      confidenceNote: confidenceNote,
    );
  }

  /// Returns a copy with one transaction removed - used when the owner
  /// rejects just ONE line of a multi-transaction result, not all of it.
  VoiceParseResult withoutTransactionAt(int index) {
    final newList = List<VoiceTransaction>.from(transactions)..removeAt(index);
    return VoiceParseResult(
      rawTranscript: rawTranscript,
      entryTimestamp: entryTimestamp,
      transactions: newList,
      isMultiIntent: newList.length > 1,
      confidenceNote: confidenceNote,
    );
  }
}

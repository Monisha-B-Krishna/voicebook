
enum TransactionIntent {
  booking,
  payment,
  returnItem,
  query,
  complete,
  cancel,
  unknown,
}

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
    case 'COMPLETE':
      return TransactionIntent.complete;
    case 'CANCEL':
      return TransactionIntent.cancel;
    default:
      return TransactionIntent.unknown;
  }
}

class VoiceTransaction {
  final TransactionIntent intent;
  final String? customerName;
  final String? date;
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
                        : intent == TransactionIntent.complete
                            ? 'COMPLETE'
                            : intent == TransactionIntent.cancel
                                ? 'CANCEL'
                                : 'UNKNOWN',
        'customer_name': customerName,
        'date': date,
        'item': item,
        'quantity': quantity,
        'amount': amount,
        'payment_type': paymentType,
      };

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

class VoiceParseResult {
  final String rawTranscript;
  final String entryTimestamp;
  final List<VoiceTransaction> transactions;
  final bool isMultiIntent;
  final String? confidenceNote;
  final int? bookingId;

  VoiceParseResult({
    required this.rawTranscript,
    required this.entryTimestamp,
    required this.transactions,
    required this.isMultiIntent,
    this.confidenceNote,
    this.bookingId,
  });

  factory VoiceParseResult.fromJson(Map<String, dynamic> json) {
    final txnList = (json['transactions'] as List?) ?? [];

    return VoiceParseResult(
      rawTranscript: json['raw_transcript'] as String? ?? '',
      entryTimestamp: json['entry_timestamp'] as String? ?? '',
      transactions: txnList
          .map((t) => VoiceTransaction.fromJson(
                t as Map<String, dynamic>,
              ))
          .toList(),
      isMultiIntent: json['is_multi_intent'] as bool? ?? false,
      confidenceNote: json['confidence_note'] as String?,
      bookingId: (json['booking_id'] as num?)?.toInt(),
    );
  }

  Map<String, dynamic> toJson() => {
        'raw_transcript': rawTranscript,
        'entry_timestamp': entryTimestamp,
        'transactions': transactions.map((t) => t.toJson()).toList(),
        'is_multi_intent': isMultiIntent,
        'confidence_note': confidenceNote,
        'booking_id': bookingId,
      };

  VoiceParseResult withTransactionAt(
    int index,
    VoiceTransaction updated,
  ) {
    final newList = List<VoiceTransaction>.from(transactions);
    newList[index] = updated;

    return VoiceParseResult(
      rawTranscript: rawTranscript,
      entryTimestamp: entryTimestamp,
      transactions: newList,
      isMultiIntent: isMultiIntent,
      confidenceNote: confidenceNote,
      bookingId: bookingId,
    );
  }

  VoiceParseResult withoutTransactionAt(int index) {
    final newList = List<VoiceTransaction>.from(transactions)
      ..removeAt(index);

    return VoiceParseResult(
      rawTranscript: rawTranscript,
      entryTimestamp: entryTimestamp,
      transactions: newList,
      isMultiIntent: newList.length > 1,
      confidenceNote: confidenceNote,
      bookingId: bookingId,
    );
  }
}

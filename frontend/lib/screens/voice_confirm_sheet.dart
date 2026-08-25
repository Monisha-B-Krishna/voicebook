import 'dart:convert';
import 'package:flutter/material.dart';
import '../l10n/app_strings.dart';
import '../models/voice_transaction.dart';
import '../services/api_service.dart';
import '../services/audio_service.dart';
import '../theme/app_theme.dart';

/// Shown after the owner speaks. Reads back EVERY transaction the NLU
/// extracted (this could be 1 or several - a multi-item booking, a
/// booking + payment together, or bookings for different customers) and
/// requires an explicit confirmation before anything is saved.
///
/// Confirmation can happen either by TAPPING a button, or by SPEAKING a
/// reply (tap the mic, say "yes"/"ಹೌದು" or "no"/"ಇಲ್ಲ") - the transcribed
/// reply is keyword-matched, same approach as the local desktop demo
/// pipeline's confirm.py.
class VoiceConfirmSheet extends StatefulWidget {
  const VoiceConfirmSheet({
    super.key,
    required this.result,
    required this.api,
    required this.audio,
    required this.onConfirm,
    required this.onReject,
  });

  final VoiceParseResult result;
  final ApiService api;
  final AudioService audio;
  final void Function(VoiceParseResult finalResult) onConfirm;
  final VoidCallback onReject;

  @override
  State<VoiceConfirmSheet> createState() => _VoiceConfirmSheetState();
}

// Keyword sets for matching a spoken yes/no reply - same words used in
// the local desktop demo pipeline, both English/transliterated and
// actual Kannada script (Sarvam ASR transcribes spoken Kannada into
// Kannada script, not Latin letters).
const _confirmWords = {
  'yes', 'y', 'confirm', 'ok', 'correct',
  'haudu', 'houdu', 'sari',
  'ಹೌದು', 'ಸರಿ', 'ಹ್ಮ್',
};
const _rejectWords = {
  'no', 'n', 'cancel', 'wrong',
  'beda', 'illa', 'tappu',
  'ಬೇಡ', 'ಇಲ್ಲ', 'ತಪ್ಪು',
};

class _VoiceConfirmSheetState extends State<VoiceConfirmSheet> {
  late VoiceParseResult _current;
  bool _isListening = false;
  bool _isProcessingReply = false;
  String? _lastHeardText;

  @override
  void initState() {
    super.initState();
    _current = widget.result;
  }

  String _intentLabel(BuildContext context, TransactionIntent intent) {
    switch (intent) {
      case TransactionIntent.booking:
        return context.tr('title_new_booking');
      case TransactionIntent.payment:
        return context.tr('title_payment_received');
      case TransactionIntent.returnItem:
        return context.tr('title_items_returned');
      case TransactionIntent.query:
        return context.tr('title_answer');
      case TransactionIntent.unknown:
        return context.tr('title_not_understood');
    }
  }

  void _removeTransaction(int index) {
    setState(() {
      _current = _current.withoutTransactionAt(index);
    });
  }

  Future<void> _listenForSpokenReply() async {
    setState(() {
      _isListening = true;
      _lastHeardText = null;
    });

    try {
      await widget.audio.startRecording();
    } catch (e) {
      setState(() => _isListening = false);
      return;
    }

    // Record for a fixed short window - long enough for "yes"/"no" or a
    // short phrase, short enough to feel responsive. A manual stop button
    // could be added later, but a fixed window keeps this simple and
    // avoids a second tap just to stop.
    await Future.delayed(const Duration(seconds: 3));

    final path = await widget.audio.stopRecording();
    setState(() {
      _isListening = false;
      _isProcessingReply = true;
    });

    if (path == null) {
      setState(() => _isProcessingReply = false);
      return;
    }

    try {
      final transcript = await widget.api.transcribeOnly(path);
      if (!mounted) return;

      setState(() {
        _lastHeardText = transcript;
        _isProcessingReply = false;
      });

      final lower = transcript.toLowerCase();
      final isConfirm = _confirmWords.any((w) => lower.contains(w));
      final isReject = _rejectWords.any((w) => lower.contains(w));

      if (isConfirm && !isReject) {
        widget.onConfirm(_current);
      } else if (isReject && !isConfirm) {
        widget.onReject();
      }
      // If ambiguous (both or neither matched), do nothing - the owner
      // can try again or just tap a button instead.
    } catch (e) {
      if (!mounted) return;
      setState(() => _isProcessingReply = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final hasAnyTransactions = _current.transactions.isNotEmpty;

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 40,
                height: 4,
                margin: const EdgeInsets.only(bottom: 16),
                decoration: BoxDecoration(color: Colors.grey.shade300, borderRadius: BorderRadius.circular(2)),
              ),
            ),
            Text(
              _current.transactions.length > 1
                  ? '${_current.transactions.length} ${context.tr('title_new_booking')}'
                  : (hasAnyTransactions
                      ? _intentLabel(context, _current.transactions.first.intent)
                      : context.tr('title_not_understood')),
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.textDark),
            ),
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(color: AppTheme.surface, borderRadius: BorderRadius.circular(10)),
              child: Text('"${_current.rawTranscript}"',
                  style: const TextStyle(fontStyle: FontStyle.italic, color: AppTheme.textMuted, fontSize: 13)),
            ),
            const SizedBox(height: 16),

            if (!hasAnyTransactions)
              Text(
                context.tr('not_understood_fallback'),
                style: const TextStyle(fontSize: 15, color: AppTheme.danger),
              )
            else
              ...List.generate(_current.transactions.length, (i) {
                final txn = _current.transactions[i];
                return Container(
                  margin: const EdgeInsets.only(bottom: 10),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    border: Border.all(color: Colors.grey.shade200),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            _intentLabel(context, txn.intent),
                            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                          ),
                          if (_current.transactions.length > 1)
                            IconButton(
                              icon: const Icon(Icons.close, size: 18, color: AppTheme.textMuted),
                              onPressed: () => _removeTransaction(i),
                              tooltip: context.tr('btn_no_discard'),
                            ),
                        ],
                      ),
                      if (txn.customerName != null) _row(context, context.tr('label_customer'), txn.customerName!),
                      if (txn.date != null) _row(context, context.tr('label_date'), txn.date!),
                      if (txn.item != null && txn.quantity != null)
                        _row(context, context.tr('label_items'), '${txn.quantity} ${txn.item}'),
                      if (txn.amount != null && txn.amount! > 0)
                        _row(context, context.tr('label_advance'), '₹${txn.amount!.toStringAsFixed(0)}'),
                    ],
                  ),
                );
              }),

            const SizedBox(height: 12),

            // Voice reply option - tap to speak "yes" or "no" instead of
            // tapping a button.
            if (hasAnyTransactions)
              Center(
                child: Column(
                  children: [
                    if (_lastHeardText != null)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 6),
                        child: Text('Heard: "$_lastHeardText"',
                            style: const TextStyle(fontSize: 12, color: AppTheme.textMuted, fontStyle: FontStyle.italic)),
                      ),
                    OutlinedButton.icon(
                      onPressed: (_isListening || _isProcessingReply) ? null : _listenForSpokenReply,
                      icon: _isListening
                          ? const Icon(Icons.mic, color: AppTheme.danger)
                          : _isProcessingReply
                              ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                              : const Icon(Icons.mic_none),
                      label: Text(
                        _isListening
                            ? 'Listening...'
                            : _isProcessingReply
                                ? 'Understanding...'
                                : 'Or speak your answer',
                      ),
                    ),
                  ],
                ),
              ),

            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: widget.onReject,
                    style: OutlinedButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 14)),
                    child: Text(context.tr('btn_no_discard')),
                  ),
                ),
                if (hasAnyTransactions) ...[
                  const SizedBox(width: 12),
                  Expanded(
                    child: ElevatedButton(
                      onPressed: () => widget.onConfirm(_current),
                      style: ElevatedButton.styleFrom(backgroundColor: AppTheme.success),
                      child: Text(context.tr('btn_yes_save')),
                    ),
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _row(BuildContext context, String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 84,
            child: Text(label, style: const TextStyle(color: AppTheme.textMuted, fontSize: 13)),
          ),
          Expanded(child: Text(value, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14.5))),
        ],
      ),
    );
  }
}

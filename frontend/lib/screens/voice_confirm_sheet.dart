
import 'dart:async';

import 'package:flutter/material.dart';

import '../l10n/app_strings.dart';
import '../models/voice_transaction.dart';
import '../services/api_service.dart';
import '../services/audio_service.dart';
import '../theme/app_theme.dart';

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
  final Future<void> Function(VoiceParseResult finalResult) onConfirm;
  final VoidCallback onReject;

  @override
  State<VoiceConfirmSheet> createState() => _VoiceConfirmSheetState();
}

const Set<String> _confirmWords = {
  'yes', 'y', 'confirm', 'ok', 'okay', 'correct',
  'haudu', 'houdu', 'sari', 'haan', 'haan seri',
  'haan sari', 'haan ji', 'yes save',
  'ಹೌದು', 'ಸರಿ', 'ಹಾಂ', 'ಹಾಂ ಸರಿ', 'ಹೌದು ಸರಿ',
  'ಆಯ್ತು', 'ಆಯಿತು',
};

const Set<String> _rejectWords = {
  'no', 'n', 'nope', 'cancel', 'wrong',
  'beda', 'illa', 'alla', 'tappu',
  'sari illa', 'sari alla', 'haan beda',
  'ಬೇಡ', 'ಇಲ್ಲ', 'ಅಲ್ಲ', 'ತಪ್ಪು',
  'ಸರಿ ಇಲ್ಲ', 'ಸರಿ ಅಲ್ಲ',
};

class _VoiceConfirmSheetState extends State<VoiceConfirmSheet> {
  late VoiceParseResult _current;

  bool _isListening = false;
  bool _isProcessingReply = false;
  bool _isSaving = false;

  String? _lastHeardText;

  @override
  void initState() {
    super.initState();
    _current = widget.result;
  }

  String _normalize(String input) {
    return input
        .toLowerCase()
        .replaceAll(RegExp(r'[^\p{L}\p{N}\s]', unicode: true), ' ')
        .replaceAll(RegExp(r'\s+'), ' ')
        .trim();
  }

  bool _containsPhrase(String transcript, String phrase) {
    return ' $transcript '.contains(' $phrase ');
  }

  String? _classifyReply(String transcript) {
    final normalized = _normalize(transcript);
    if (normalized.isEmpty) return null;

    // Check rejection first: "sari illa" must never become "yes".
    final rejected = _rejectWords.any(
      (word) => _containsPhrase(normalized, _normalize(word)),
    );

    if (rejected) return 'no';

    final confirmed = _confirmWords.any(
      (word) => _containsPhrase(normalized, _normalize(word)),
    );

    if (confirmed) return 'yes';

    return null;
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
      case TransactionIntent.complete:
        return 'Mark Order Complete';
      case TransactionIntent.cancel:
        return 'Cancel Order';
      case TransactionIntent.unknown:
        return context.tr('title_not_understood');
    }
  }

  void _removeTransaction(int index) {
    if (_isSaving) return;
    setState(() {
      _current = _current.withoutTransactionAt(index);
    });
  }

  Future<void> _handleConfirm() async {
    if (_isSaving || _current.transactions.isEmpty) return;

    setState(() => _isSaving = true);

    // Allow Flutter to paint the saving indicator before the API call.
    await WidgetsBinding.instance.endOfFrame;

    if (!mounted) return;

    try {
      await widget.onConfirm(_current);
    } catch (e) {
      if (!mounted) return;

      setState(() => _isSaving = false);
      debugPrint('Voice transaction save failed: $e');
    }
  }

  void _handleReject() {
    if (_isSaving) return;
    widget.onReject();
  }

  Future<void> _listenForSpokenReply() async {
    if (_isSaving || _isListening || _isProcessingReply) return;

    setState(() {
      _isListening = true;
      _lastHeardText = null;
    });

    try {
      await widget.audio.startRecording();
      await Future.delayed(const Duration(seconds: 3));

      if (!mounted) {
        await widget.audio.cancelRecording();
        return;
      }

      final audioBytes = await widget.audio.stopRecording();

      if (!mounted) return;

      setState(() {
        _isListening = false;
        _isProcessingReply = true;
      });

      if (audioBytes == null || audioBytes.isEmpty) {
        if (mounted) {
          setState(() => _isProcessingReply = false);
        }
        return;
      }

      final transcript = await widget.api.transcribeOnly(audioBytes);

      if (!mounted) return;

      final reply = _classifyReply(transcript);

      setState(() {
        _lastHeardText = transcript;
        _isProcessingReply = false;
      });

      if (reply == 'no') {
        _handleReject();
      } else if (reply == 'yes') {
        await _handleConfirm();
      } else {
        setState(() {
          _lastHeardText = '$transcript  —  Please say Yes or No again.';
        });
      }
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _isListening = false;
        _isProcessingReply = false;
        _lastHeardText = 'Could not understand. Please try again.';
      });

      debugPrint('Spoken confirmation failed: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final hasAnyTransactions = _current.transactions.isNotEmpty;
    final isBusy = _isListening || _isProcessingReply || _isSaving;

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
                decoration: BoxDecoration(
                  color: Colors.grey.shade300,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            Text(
              _current.transactions.length > 1
                  ? '${_current.transactions.length} ${context.tr('title_new_booking')}'
                  : (hasAnyTransactions
                      ? _intentLabel(
                          context,
                          _current.transactions.first.intent,
                        )
                      : context.tr('title_not_understood')),
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: AppTheme.textDark,
              ),
            ),
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: AppTheme.surface,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                '"${_current.rawTranscript}"',
                style: const TextStyle(
                  fontStyle: FontStyle.italic,
                  color: AppTheme.textMuted,
                  fontSize: 13,
                ),
              ),
            ),
            const SizedBox(height: 16),
            if (!hasAnyTransactions)
              Text(
                context.tr('not_understood_fallback'),
                style: const TextStyle(
                  fontSize: 15,
                  color: AppTheme.danger,
                ),
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
                            style: const TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 14,
                            ),
                          ),
                          if (_current.transactions.length > 1)
                            IconButton(
                              icon: const Icon(
                                Icons.close,
                                size: 18,
                                color: AppTheme.textMuted,
                              ),
                              onPressed: isBusy
                                  ? null
                                  : () => _removeTransaction(i),
                              tooltip: context.tr('btn_no_discard'),
                            ),
                        ],
                      ),
                      if (txn.customerName != null)
                        _row(
                          context,
                          context.tr('label_customer'),
                          txn.customerName!,
                        ),
                      if (txn.date != null)
                        _row(context, context.tr('label_date'), txn.date!),
                      if (txn.item != null && txn.quantity != null)
                        _row(
                          context,
                          context.tr('label_items'),
                          '${txn.quantity} ${txn.item}',
                        ),
                      if (txn.amount != null && txn.amount! > 0)
                        _row(
                          context,
                          context.tr('label_advance'),
                          '₹${txn.amount!.toStringAsFixed(0)}',
                        ),
                    ],
                  ),
                );
              }),
            const SizedBox(height: 12),

            // Persistent visual feedback while the save request is running.
            if (_isSaving)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                margin: const EdgeInsets.only(bottom: 12),
                decoration: BoxDecoration(
                  color: AppTheme.surface,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Row(
                  children: [
                    SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2.5),
                    ),
                    SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Saving your transaction...',
                        style: TextStyle(
                          fontWeight: FontWeight.w600,
                          color: AppTheme.textDark,
                        ),
                      ),
                    ),
                  ],
                ),
              ),

            if (hasAnyTransactions)
              Center(
                child: Column(
                  children: [
                    if (_lastHeardText != null)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 6),
                        child: Text(
                          'Heard: "$_lastHeardText"',
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            fontSize: 12,
                            color: AppTheme.textMuted,
                            fontStyle: FontStyle.italic,
                          ),
                        ),
                      ),
                    OutlinedButton.icon(
                      onPressed: isBusy ? null : _listenForSpokenReply,
                      icon: _isListening
                          ? const Icon(Icons.mic, color: AppTheme.danger)
                          : _isProcessingReply || _isSaving
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                  ),
                                )
                              : const Icon(Icons.mic_none),
                      label: Text(
                        _isListening
                            ? 'Listening...'
                            : _isProcessingReply
                                ? 'Understanding...'
                                : _isSaving
                                    ? 'Saving...'
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
                    onPressed: isBusy ? null : _handleReject,
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                    ),
                    child: Text(context.tr('btn_no_discard')),
                  ),
                ),
                if (hasAnyTransactions) ...[
                  const SizedBox(width: 12),
                  Expanded(
                    child: ElevatedButton(
                      onPressed: isBusy ? null : _handleConfirm,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.success,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                      ),
                      child: _isSaving
                          ? const Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                SizedBox(
                                  width: 18,
                                  height: 18,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: Colors.white,
                                  ),
                                ),
                                SizedBox(width: 10),
                                Text(
                                  'Saving...',
                                  style: TextStyle(color: Colors.white),
                                ),
                              ],
                            )
                          : Text(context.tr('btn_yes_save')),
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
            child: Text(
              label,
              style: const TextStyle(
                color: AppTheme.textMuted,
                fontSize: 13,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(
                fontWeight: FontWeight.w600,
                fontSize: 14.5,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

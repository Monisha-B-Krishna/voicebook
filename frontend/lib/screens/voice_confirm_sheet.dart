import 'package:flutter/material.dart';
import '../l10n/app_strings.dart';
import '../models/voice_transaction.dart';
import '../theme/app_theme.dart';

/// Shown after the owner speaks. Reads back EVERY transaction the NLU
/// extracted (this could be 1 or several - a multi-item booking, a
/// booking + payment together, or bookings for different customers) and
/// requires an explicit confirmation before anything is saved.
///
/// This replaces the old single-VoiceIntent version - the real backend
/// can return multiple transactions from one utterance, and throwing
/// that away to only show one would silently lose real data.
class VoiceConfirmSheet extends StatefulWidget {
  const VoiceConfirmSheet({
    super.key,
    required this.result,
    required this.onConfirm,
    required this.onReject,
  });

  final VoiceParseResult result;
  final void Function(VoiceParseResult finalResult) onConfirm;
  final VoidCallback onReject;

  @override
  State<VoiceConfirmSheet> createState() => _VoiceConfirmSheetState();
}

class _VoiceConfirmSheetState extends State<VoiceConfirmSheet> {
  late VoiceParseResult _current;

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
                  ? '${_current.transactions.length} ${context.tr('title_new_booking')}' // e.g. "2 transactions"
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
              // One card per transaction - the owner can reject individual
              // lines (e.g. one item was misheard) without discarding the
              // whole utterance.
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
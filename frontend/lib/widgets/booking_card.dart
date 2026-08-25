import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../l10n/app_strings.dart';
import '../models/booking.dart';
import '../theme/app_theme.dart';

class BookingCard extends StatelessWidget {
  const BookingCard({super.key, required this.booking, this.onTap});

  final Booking booking;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final dateStr = DateFormat('EEE, d MMM').format(booking.eventDate);
    final itemsStr = booking.items.map((i) => '${i.qty} ${i.itemName}').join(', ');
    final hasBalance = booking.balanceDue > 0;

    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              CircleAvatar(
                radius: 22,
                backgroundColor: AppTheme.accent.withOpacity(0.25),
                child: Text(
                  booking.customerName.isNotEmpty ? booking.customerName[0].toUpperCase() : '?',
                  style: const TextStyle(color: AppTheme.primaryDark, fontWeight: FontWeight.bold),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(booking.customerName,
                        style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15.5)),
                    const SizedBox(height: 2),
                    Text('$dateStr · $itemsStr',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: AppTheme.textMuted, fontSize: 12.5)),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    hasBalance ? '₹${booking.balanceDue.toStringAsFixed(0)}' : context.tr('paid'),
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: hasBalance ? AppTheme.danger : AppTheme.success,
                    ),
                  ),
                  Text(hasBalance ? context.tr('due') : '',
                      style: const TextStyle(fontSize: 11, color: AppTheme.textMuted)),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

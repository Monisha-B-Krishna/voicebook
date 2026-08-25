import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../l10n/app_strings.dart';
import '../models/booking.dart';
import '../providers/app_data_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/stat_card.dart';
import '../widgets/language_toggle_button.dart';

class ReportsScreen extends StatelessWidget {
  const ReportsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final data = context.watch<AppDataProvider>();
    final now = DateTime.now();

    final monthlyIncome = data.payments
        .where((p) => p.date.month == now.month && p.date.year == now.year)
        .fold(0.0, (sum, p) => sum + p.amount);

    final revenue = data.bookings
        .where((b) => b.status != BookingStatus.cancelled)
        .fold(0.0, (sum, b) => sum + b.totalAmount);

    final todaysEvents = data.todaysBookings.length;

    return Scaffold(
      appBar: AppBar(
        title: Text(context.tr('reports')),
        actions: const [LanguageToggleButton()],
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              childAspectRatio: 1.0,
              children: [
                StatCard(
                  label: context.tr('total_revenue'),
                  value: '₹${revenue.toStringAsFixed(0)}',
                  icon: Icons.trending_up_rounded,
                  color: AppTheme.success,
                ),
                StatCard(
                  label: context.tr('pending_balance'),
                  value: '₹${data.totalPendingBalance.toStringAsFixed(0)}',
                  icon: Icons.hourglass_bottom_rounded,
                  color: AppTheme.danger,
                ),
                StatCard(
                  label: context.tr('todays_events'),
                  value: '$todaysEvents',
                  icon: Icons.today_rounded,
                  color: AppTheme.accent,
                ),
                StatCard(
                  label: context.tr('monthly_income'),
                  value: '₹${monthlyIncome.toStringAsFixed(0)}',
                  icon: Icons.calendar_month_rounded,
                ),
              ],
            ),
            const SizedBox(height: 28),
            Text(context.tr('recent_payments'), style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            if (data.payments.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 16),
                child: Text(context.tr('no_payments_yet'), style: const TextStyle(color: AppTheme.textMuted)),
              )
            else
              ...data.payments.reversed.take(10).map((p) => Card(
                    child: ListTile(
                      leading: const CircleAvatar(
                        backgroundColor: AppTheme.success,
                        child: Icon(Icons.currency_rupee_rounded, color: Colors.white, size: 18),
                      ),
                      title: Text(p.customerName, style: const TextStyle(fontWeight: FontWeight.w600)),
                      subtitle: Text(p.note.isNotEmpty ? p.note : context.tr('payment_received')),
                      trailing: Text('₹${p.amount.toStringAsFixed(0)}',
                          style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.success)),
                    ),
                  )),
          ],
        ),
      ),
    );
  }
}
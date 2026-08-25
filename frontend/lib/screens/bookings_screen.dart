import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../l10n/app_strings.dart';
import '../models/booking.dart';
import '../providers/app_data_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/booking_card.dart';
import '../widgets/language_toggle_button.dart';

class BookingsScreen extends StatefulWidget {
  const BookingsScreen({super.key});

  @override
  State<BookingsScreen> createState() => _BookingsScreenState();
}

class _BookingsScreenState extends State<BookingsScreen> {
  String _query = '';
  BookingStatus? _filter;

  @override
  Widget build(BuildContext context) {
    final data = context.watch<AppDataProvider>();
    var list = List<Booking>.from(data.bookings)
      ..sort((a, b) => b.eventDate.compareTo(a.eventDate));

    if (_filter != null) {
      list = list.where((b) => b.status == _filter).toList();
    }
    if (_query.isNotEmpty) {
      list = list.where((b) => b.customerName.toLowerCase().contains(_query.toLowerCase())).toList();
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(context.tr('bookings')),
        actions: const [LanguageToggleButton()],
      ),
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
              child: TextField(
                decoration: InputDecoration(
                  hintText: context.tr('search_customer_name'),
                  prefixIcon: const Icon(Icons.search),
                ),
                onChanged: (v) => setState(() => _query = v),
              ),
            ),
            SizedBox(
              height: 44,
              child: ListView(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 16),
                children: [
                  _chip(context.tr('filter_all'), null),
                  _chip(context.tr('filter_upcoming'), BookingStatus.upcoming),
                  _chip(context.tr('filter_completed'), BookingStatus.completed),
                  _chip(context.tr('filter_cancelled'), BookingStatus.cancelled),
                ],
              ),
            ),
            const SizedBox(height: 6),
            Expanded(
              child: list.isEmpty
                  ? Center(
                      child: Text(context.tr('no_bookings_found'), style: const TextStyle(color: AppTheme.textMuted)),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.fromLTRB(16, 0, 16, 20),
                      itemCount: list.length,
                      itemBuilder: (context, i) {
                        final booking = list[i];
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: BookingCard(
                            booking: booking,
                            onTap: () => _showDetail(context, booking),
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _chip(String label, BookingStatus? status) {
    final selected = _filter == status;
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: ChoiceChip(
        label: Text(label),
        selected: selected,
        onSelected: (_) => setState(() => _filter = status),
        selectedColor: AppTheme.primary,
        labelStyle: TextStyle(color: selected ? Colors.white : AppTheme.textDark, fontSize: 12.5),
      ),
    );
  }

  void _showDetail(BuildContext context, Booking booking) {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (sheetContext) => Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(booking.customerName, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            Text(DateFormat('EEEE, d MMMM yyyy').format(booking.eventDate),
                style: const TextStyle(color: AppTheme.textMuted)),
            const SizedBox(height: 16),
            ...booking.items.map((i) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 3),
                  child: Row(
                    children: [
                      const Icon(Icons.circle, size: 6, color: AppTheme.textMuted),
                      const SizedBox(width: 8),
                      Text('${i.qty} × ${i.itemName}'),
                    ],
                  ),
                )),
            const Divider(height: 28),
            _detailRow(sheetContext, sheetContext.tr('total_amount'), '₹${booking.totalAmount.toStringAsFixed(0)}'),
            _detailRow(sheetContext, sheetContext.tr('advance_paid'), '₹${booking.advancePaid.toStringAsFixed(0)}'),
            _detailRow(
              sheetContext,
              sheetContext.tr('balance_due'),
              '₹${booking.balanceDue.toStringAsFixed(0)}',
              color: booking.balanceDue > 0 ? AppTheme.danger : AppTheme.success,
            ),
            _detailRow(sheetContext, sheetContext.tr('returned'),
                booking.returned ? sheetContext.tr('yes') : sheetContext.tr('no')),
          ],
        ),
      ),
    );
  }

  Widget _detailRow(BuildContext context, String label, String value, {Color? color}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: AppTheme.textMuted)),
          Text(value, style: TextStyle(fontWeight: FontWeight.bold, color: color ?? AppTheme.textDark)),
        ],
      ),
    );
  }
}

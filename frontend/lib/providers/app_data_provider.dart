import 'package:flutter/material.dart';
import '../models/booking.dart';
import '../models/customer.dart';
import '../models/inventory_item.dart';
import '../models/payment.dart';
import '../services/api_service.dart';

/// Holds all business data for the app, fetched from the REAL backend.
///
/// IMPORTANT: the backend does NOT provide one combined "booking with
/// items and payments" endpoint - it exposes flat tables (bookings,
/// booking_items, payments, returns, customers, inventory) separately.
/// This class does the joining client-side, since that endpoint doesn't
/// exist yet. A future improvement would be adding a combined endpoint
/// server-side instead of joining on the phone every time.
///
/// This REPLACES the old version's hardcoded mock seed data and its
/// crude local reimplementations of business logic (availability
/// checking, alias matching) - those now correctly live server-side,
/// in voice_transactions.py and matching.py, and their results/errors
/// are simply displayed here, not recomputed.
class AppDataProvider extends ChangeNotifier {
  List<Customer> customers = [];
  List<InventoryItem> inventory = [];
  List<Booking> bookings = [];
  List<Payment> payments = [];

  bool isLoading = false;
  String? loadError;

  /// Fetches everything fresh from the backend and rebuilds all local
  /// lists via client-side joins. Call this on app startup, and again
  /// after any voice transaction is saved.
  Future<void> refreshFromBackend(ApiService api) async {
    isLoading = true;
    loadError = null;
    notifyListeners();

    try {
      final results = await Future.wait([
        api.fetchCustomers(),
        api.fetchInventory(),
        api.fetchBookings(),
        api.fetchPayments(),
      ]);

      final rawCustomers = results[0];
      final rawInventory = results[1];
      final rawBookings = results[2];
      final rawPayments = results[3];

      // Booking items and returns aren't behind simple ApiService methods
      // yet (they weren't needed for the voice flow itself) - fetch them
      // directly here for the join.
      final rawBookingItems = List<Map<String, dynamic>>.from(
          await api.fetchRaw('/booking-items/') as List);
      final rawReturns = List<Map<String, dynamic>>.from(
          await api.fetchRaw('/returns/') as List);

      // ---- Build lookup maps first ----
      final customerNameById = {
        for (final c in rawCustomers) c['customer_id'] as int: c['name'] as String
      };
      final itemNameById = {
        for (final i in rawInventory) i['item_id'] as int: i['item_name'] as String
      };

      // ---- Customers (with aliases fetched per-customer) ----
      final newCustomers = <Customer>[];
      for (final c in rawCustomers) {
        final aliasRes = await api.fetchRaw('/customers/${c['customer_id']}/aliases');
        final aliasNames = (aliasRes as List).map((a) => a['alias_name'] as String).toList();
        newCustomers.add(Customer(
          id: c['customer_id'].toString(),
          name: c['name'] as String,
          aliases: aliasNames,
          phone: c['phone'] as String? ?? '',
        ));
      }
      customers = newCustomers;

      // ---- Inventory ----
      // NOTE: the backend's `available_quantity` field is used as the
      // TOTAL owned stock ceiling in booking_items.py's availability
      // check (not a live decrementing counter for bookings - only
      // returns.py increments it). We compute "currently booked" here
      // ourselves by summing active booking_items per item, to show a
      // meaningful bookedQty/availableQty split in the UI.
      final activeBookingIds = rawBookings
          .where((b) => b['status'] != 'cancelled')
          .map((b) => b['booking_id'] as int)
          .toSet();

      inventory = rawInventory.map((i) {
        final itemId = i['item_id'] as int;
        final bookedQty = rawBookingItems
            .where((bi) => bi['item_id'] == itemId && activeBookingIds.contains(bi['booking_id']))
            .fold<int>(0, (sum, bi) => sum + (bi['quantity'] as int));
        return InventoryItem(
          id: itemId.toString(),
          name: i['item_name'] as String,
          totalQty: i['available_quantity'] as int,
          bookedQty: bookedQty,
        );
      }).toList();

      // ---- Payments (need customer name via booking -> customer join) ----
      final customerIdByBookingId = {
        for (final b in rawBookings) b['booking_id'] as int: b['customer_id'] as int
      };
      payments = rawPayments.map((p) {
        final bookingId = p['booking_id'] as int;
        final custId = customerIdByBookingId[bookingId];
        return Payment(
          id: p['payment_id'].toString(),
          bookingId: bookingId.toString(),
          customerName: custId != null ? (customerNameById[custId] ?? 'Unknown') : 'Unknown',
          amount: (p['amount'] as num).toDouble(),
          date: DateTime.tryParse(p['payment_date'] as String? ?? '') ?? DateTime.now(),
          note: p['payment_method'] as String? ?? '',
        );
      }).toList();

      // ---- Bookings (join items, payments, returns) ----
      final returnedBookingIds = rawReturns
          .map((r) => r['booking_id'] as int)
          .toSet();

      bookings = rawBookings.map((b) {
        final bookingId = b['booking_id'] as int;
        final custId = b['customer_id'] as int;

        final items = rawBookingItems
            .where((bi) => bi['booking_id'] == bookingId)
            .map((bi) => BookingLineItem(
                  itemName: itemNameById[bi['item_id']] ?? 'Unknown item',
                  qty: bi['quantity'] as int,
                ))
            .toList();

        final advancePaid = rawPayments
            .where((p) => p['booking_id'] == bookingId && p['payment_status'] == 'paid')
            .fold<double>(0.0, (sum, p) => sum + (p['amount'] as num).toDouble());

        final eventDate = DateTime.tryParse(b['event_date'] as String? ?? '') ?? DateTime.now();

        BookingStatus status;
        if (b['status'] == 'cancelled') {
          status = BookingStatus.cancelled;
        } else if (eventDate.isBefore(DateTime.now().subtract(const Duration(days: 1)))) {
          status = BookingStatus.completed;
        } else {
          status = BookingStatus.upcoming;
        }

        return Booking(
          id: bookingId.toString(),
          customerId: custId.toString(),
          customerName: customerNameById[custId] ?? 'Unknown',
          eventDate: eventDate,
          items: items,
          advancePaid: advancePaid,
          totalAmount: (b['total_amount'] as num).toDouble(),
          status: status,
          returned: returnedBookingIds.contains(bookingId),
        );
      }).toList();

      isLoading = false;
    } catch (e) {
      isLoading = false;
      loadError = e.toString();
    }

    notifyListeners();
  }

  // ---------- Derived / read helpers (unchanged logic, now over real data) ----------

  List<Booking> get todaysBookings {
    final now = DateTime.now();
    return bookings
        .where((b) =>
            b.eventDate.year == now.year &&
            b.eventDate.month == now.month &&
            b.eventDate.day == now.day)
        .toList();
  }

  List<Booking> get upcomingBookings => bookings
      .where((b) =>
          b.status == BookingStatus.upcoming &&
          b.eventDate.isAfter(DateTime.now().subtract(const Duration(days: 1))))
      .toList()
    ..sort((a, b) => a.eventDate.compareTo(b.eventDate));

  double get totalPendingBalance =>
      bookings.where((b) => b.status != BookingStatus.cancelled).fold(0.0, (sum, b) => sum + b.balanceDue);

  double customerBalance(String customerName) {
    return bookings
        .where((b) => b.customerName.toLowerCase() == customerName.toLowerCase() && b.status != BookingStatus.cancelled)
        .fold(0.0, (sum, b) => sum + b.balanceDue);
  }
}

class BookingLineItem {
  final String itemName;
  final int qty;

  BookingLineItem({required this.itemName, required this.qty});

  Map<String, dynamic> toJson() => {'name': itemName, 'qty': qty};

  factory BookingLineItem.fromJson(Map<String, dynamic> json) =>
      BookingLineItem(itemName: json['name'] as String, qty: json['qty'] as int);
}

enum BookingStatus { upcoming, completed, cancelled }

class Booking {
  final String id;
  final String customerId;
  final String customerName;
  final DateTime eventDate;
  final List<BookingLineItem> items;
  final double advancePaid;
  final double totalAmount;
  BookingStatus status;
  bool returned;

  Booking({
    required this.id,
    required this.customerId,
    required this.customerName,
    required this.eventDate,
    required this.items,
    required this.advancePaid,
    required this.totalAmount,
    this.status = BookingStatus.upcoming,
    this.returned = false,
  });

  double get balanceDue => (totalAmount - advancePaid).clamp(0, double.infinity);
}

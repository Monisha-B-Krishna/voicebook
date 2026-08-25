class Payment {
  final String id;
  final String bookingId;
  final String customerName;
  final double amount;
  final DateTime date;
  final String note;

  Payment({
    required this.id,
    required this.bookingId,
    required this.customerName,
    required this.amount,
    required this.date,
    this.note = '',
  });
}

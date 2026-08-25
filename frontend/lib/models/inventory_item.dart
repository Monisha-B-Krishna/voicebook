class InventoryItem {
  final String id;
  final String name; // e.g. "Vessels", "Chairs", "Canopies"
  final int totalQty;
  int bookedQty; // quantity currently committed against active bookings

  InventoryItem({
    required this.id,
    required this.name,
    required this.totalQty,
    this.bookedQty = 0,
  });

  int get availableQty => totalQty - bookedQty;
  double get utilization => totalQty == 0 ? 0 : bookedQty / totalQty;
}

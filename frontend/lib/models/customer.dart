class Customer {
  final String id;
  final String name;
  final List<String> aliases; // nicknames / alternate names used in speech
  final String phone;

  Customer({
    required this.id,
    required this.name,
    this.aliases = const [],
    this.phone = '',
  });

  /// Returns true if [spokenName] matches this customer's name or any alias,
  /// case-insensitively. In the real backend this resolution is done by the
  /// LLM/NLU layer against the customer table; here it's mocked simply.
  bool matches(String spokenName) {
    final q = spokenName.trim().toLowerCase();
    if (name.toLowerCase() == q) return true;
    return aliases.any((a) => a.toLowerCase() == q);
  }
}

import 'package:flutter/material.dart';
import '../l10n/app_strings.dart';
import '../models/customer.dart';
import '../theme/app_theme.dart';

class CustomerCard extends StatelessWidget {
  const CustomerCard({super.key, required this.customer, required this.balance, this.onTap});

  final Customer customer;
  final double balance;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        onTap: onTap,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        leading: CircleAvatar(
          backgroundColor: AppTheme.primary.withOpacity(0.12),
          child: Text(customer.name.isNotEmpty ? customer.name[0].toUpperCase() : '?',
              style: const TextStyle(color: AppTheme.primaryDark, fontWeight: FontWeight.bold)),
        ),
        title: Text(customer.name, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(
          customer.aliases.isNotEmpty
              ? '${context.tr('aka')} ${customer.aliases.join(", ")}'
              : customer.phone,
          style: const TextStyle(fontSize: 12.5),
        ),
        trailing: balance > 0
            ? Text('₹${balance.toStringAsFixed(0)}',
                style: const TextStyle(color: AppTheme.danger, fontWeight: FontWeight.bold))
            : const Icon(Icons.check_circle, color: AppTheme.success, size: 20),
      ),
    );
  }
}

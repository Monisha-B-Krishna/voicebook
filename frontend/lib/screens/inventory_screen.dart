import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../l10n/app_strings.dart';
import '../providers/app_data_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/language_toggle_button.dart';

class InventoryScreen extends StatelessWidget {
  const InventoryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final data = context.watch<AppDataProvider>();

    return Scaffold(
      appBar: AppBar(
        title: Text(context.tr('inventory')),
        actions: const [LanguageToggleButton()],
      ),
      body: SafeArea(
        child: ListView.builder(
          padding: const EdgeInsets.all(16),
          itemCount: data.inventory.length,
          itemBuilder: (context, i) {
            final item = data.inventory[i];
            final lowStock = item.availableQty < item.totalQty * 0.15;
            return Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(item.name, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                        if (lowStock)
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: AppTheme.danger.withOpacity(0.1),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Text(context.tr('low_stock'),
                                style: const TextStyle(color: AppTheme.danger, fontSize: 11, fontWeight: FontWeight.w600)),
                          ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(8),
                      child: LinearProgressIndicator(
                        value: item.utilization.clamp(0, 1),
                        minHeight: 10,
                        backgroundColor: AppTheme.surface,
                        color: lowStock ? AppTheme.danger : AppTheme.primary,
                      ),
                    ),
                    const SizedBox(height: 10),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text('${context.tr('booked_colon')}: ${item.bookedQty}',
                            style: const TextStyle(color: AppTheme.textMuted, fontSize: 12.5)),
                        Text('${context.tr('available_colon')}: ${item.availableQty}',
                            style: const TextStyle(color: AppTheme.success, fontSize: 12.5, fontWeight: FontWeight.w600)),
                        Text('${context.tr('total_colon')}: ${item.totalQty}',
                            style: const TextStyle(color: AppTheme.textMuted, fontSize: 12.5)),
                      ],
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}

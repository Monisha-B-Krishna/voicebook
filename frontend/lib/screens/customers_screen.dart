import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../l10n/app_strings.dart';
import '../providers/app_data_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/customer_card.dart';
import '../widgets/language_toggle_button.dart';

class CustomersScreen extends StatefulWidget {
  const CustomersScreen({super.key});

  @override
  State<CustomersScreen> createState() => _CustomersScreenState();
}

class _CustomersScreenState extends State<CustomersScreen> {
  String _query = '';

  @override
  Widget build(BuildContext context) {
    final data = context.watch<AppDataProvider>();
    var list = data.customers.where((c) {
      if (_query.isEmpty) return true;
      final q = _query.toLowerCase();
      return c.name.toLowerCase().contains(q) || c.aliases.any((a) => a.toLowerCase().contains(q));
    }).toList();

    return Scaffold(
      appBar: AppBar(
        title: Text(context.tr('customers')),
        actions: const [LanguageToggleButton()],
      ),
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
              child: TextField(
                decoration: InputDecoration(
                  hintText: context.tr('search_name_nickname'),
                  prefixIcon: const Icon(Icons.search),
                ),
                onChanged: (v) => setState(() => _query = v),
              ),
            ),
            Expanded(
              child: list.isEmpty
                  ? Center(
                      child: Text(context.tr('no_customers_found'), style: const TextStyle(color: AppTheme.textMuted)))
                  : ListView.builder(
                      padding: const EdgeInsets.fromLTRB(16, 0, 16, 20),
                      itemCount: list.length,
                      itemBuilder: (context, i) {
                        final c = list[i];
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 4),
                          child: CustomerCard(
                            customer: c,
                            balance: data.customerBalance(c.name),
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
}

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_data_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import 'home_screen.dart';
import 'bookings_screen.dart';
import 'customers_screen.dart';
import 'inventory_screen.dart';
import 'reports_screen.dart';

/// Bottom-nav shell wrapping the five main screens. Also responsible for
/// the initial fetch of real data from the backend on app startup -
/// AppDataProvider starts EMPTY now (no more hardcoded mock seed data),
/// so this fetch is what actually populates the app with real customers,
/// inventory, bookings, and payments.
class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;

  @override
  void initState() {
    super.initState();
    // Fetch real data once the widget tree is built and providers exist.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final api = context.read<ApiService>();
      context.read<AppDataProvider>().refreshFromBackend(api);
    });
  }

  void _goToTab(int i) => setState(() => _index = i);

  @override
  Widget build(BuildContext context) {
    final data = context.watch<AppDataProvider>();

    final screens = [
      HomeScreen(onNavigateTab: _goToTab),
      const BookingsScreen(),
      const CustomersScreen(),
      const InventoryScreen(),
      const ReportsScreen(),
    ];

    return Scaffold(
      body: Column(
        children: [
          if (data.isLoading)
            const LinearProgressIndicator(minHeight: 2, color: AppTheme.primary),
          if (data.loadError != null)
            Container(
              width: double.infinity,
              color: AppTheme.danger.withOpacity(0.1),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: Text(
                'Could not load data from backend: ${data.loadError}',
                style: const TextStyle(color: AppTheme.danger, fontSize: 12.5),
              ),
            ),
          Expanded(
            child: IndexedStack(index: _index, children: screens),
          ),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: _goToTab,
        backgroundColor: Colors.white,
        indicatorColor: AppTheme.primary.withOpacity(0.12),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home), label: 'Home'),
          NavigationDestination(
              icon: Icon(Icons.event_note_outlined), selectedIcon: Icon(Icons.event_note), label: 'Bookings'),
          NavigationDestination(
              icon: Icon(Icons.people_alt_outlined), selectedIcon: Icon(Icons.people_alt), label: 'Customers'),
          NavigationDestination(
              icon: Icon(Icons.inventory_2_outlined), selectedIcon: Icon(Icons.inventory_2), label: 'Inventory'),
          NavigationDestination(
              icon: Icon(Icons.bar_chart_outlined), selectedIcon: Icon(Icons.bar_chart), label: 'Reports'),
        ],
      ),
    );
  }
}

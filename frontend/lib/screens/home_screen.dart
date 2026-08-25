import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../l10n/app_strings.dart';
import '../providers/app_data_provider.dart';
import '../services/api_service.dart';
import '../services/audio_service.dart';
import '../models/voice_transaction.dart';
import '../theme/app_theme.dart';
import '../widgets/mic_button.dart';
import '../widgets/stat_card.dart';
import '../widgets/language_toggle_button.dart';
import 'voice_confirm_sheet.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, required this.onNavigateTab});

  /// Lets Home jump to another bottom-nav tab (e.g. Bookings) on tap.
  final void Function(int tabIndex) onNavigateTab;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final AudioService _audio = AudioService();
  bool _isRecording = false;
  bool _isProcessing = false;

  @override
  void dispose() {
    _audio.dispose();
    super.dispose();
  }

  Future<void> _startRecording() async {
    try {
      await _audio.startRecording();
      setState(() => _isRecording = true);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            '${context.tr('could_not_start_recording', listen: false)}: $e',
          ),
        ),
      );
    }
  }

  Future<void> _stopRecording() async {
    // listen: false is REQUIRED here - this whole method runs from a
    // button tap (an event handler), never during build, so context.watch
    // (the default) would throw. listen: false uses context.read instead,
    // which is safe to call from anywhere.
    final notUnderstoodMsg = context.tr('not_understood_fallback', listen: false);
    final couldNotStartMsg = context.tr('could_not_start_recording', listen: false);

    setState(() {
      _isRecording = false;
      _isProcessing = true;
    });

    final path = await _audio.stopRecording();

    if (path == null) {
      setState(() => _isProcessing = false);
      return;
    }

    final api = context.read<ApiService>();

    try {
      // Calls the REAL backend: /voice/process-audio runs ASR + NLU and
      // returns a VoiceParseResult - which may contain MULTIPLE
      // transactions (multi-item booking, booking+payment together, or
      // even bookings for two different customers in one utterance).
      final result = await api.sendAudioForProcessing(path);

      if (!mounted) return;
      setState(() => _isProcessing = false);

      if (result.transactions.isEmpty) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(notUnderstoodMsg)),
        );
        return;
      }

      _showConfirmSheet(result);
    } catch (e) {
      if (!mounted) return;
      setState(() => _isProcessing = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('$couldNotStartMsg: $e')),
      );
    }
  }

  void _showConfirmSheet(VoiceParseResult result) {
    final api = context.read<ApiService>();
    // listen: false required - _showConfirmSheet is called from
    // _stopRecording, itself an event handler, never during build.
    final savedMsg = context.tr('saved_successfully', listen: false);
    final errorMsg = context.tr('could_not_start_recording', listen: false);

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(
          top: Radius.circular(24),
        ),
      ),
      builder: (sheetContext) => VoiceConfirmSheet(
        result: result,
        onConfirm: (finalResult) async {
          try {
            final saveResults = await api.saveVoiceResult(finalResult);
            if (!mounted) return;
            Navigator.pop(sheetContext);

            final errors = (saveResults['errors'] as List?) ?? [];
            if (errors.isNotEmpty) {
              // Real backend errors (e.g. "item not found in inventory",
              // "customer has multiple open bookings") - show them plainly
              // rather than pretending everything saved cleanly.
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text(errors.join('; ')),
                  backgroundColor: AppTheme.danger,
                  duration: const Duration(seconds: 5),
                ),
              );
            } else {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text(savedMsg),
                  backgroundColor: AppTheme.success,
                ),
              );
            }

            // Refresh local data from the real backend after a successful save,
            // so Bookings/Customers/Inventory/Reports screens reflect the change.
            context.read<AppDataProvider>().refreshFromBackend(api);
          } catch (e) {
            if (!mounted) return;
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('$errorMsg: $e')),
            );
          }
        },
        onReject: () {
          Navigator.pop(sheetContext);
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final data = context.watch<AppDataProvider>();

    return Scaffold(
      appBar: AppBar(
        title: Text(context.tr('app_name')),
        actions: const [
          LanguageToggleButton(),
        ],
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              '${context.tr('hello')} 👋',
              style: const TextStyle(
                fontSize: 16,
                color: AppTheme.textMuted,
              ),
            ),
            const SizedBox(height: 20),

            Center(
              child: MicButton(
                isRecording: _isRecording,
                isProcessing: _isProcessing,
                onStart: _startRecording,
                onStop: _stopRecording,
              ),
            ),

            const SizedBox(height: 28),

            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              childAspectRatio: 1.0,
              children: [
                StatCard(
                  label: context.tr('todays_bookings'),
                  value: '${data.todaysBookings.length}',
                  icon: Icons.event_available_rounded,
                  onTap: () => widget.onNavigateTab(1),
                ),
                StatCard(
                  label: context.tr('pending_balance'),
                  value:
                      '₹${data.totalPendingBalance.toStringAsFixed(0)}',
                  icon: Icons.currency_rupee_rounded,
                  color: AppTheme.danger,
                  onTap: () => widget.onNavigateTab(4),
                ),
                StatCard(
                  label: context.tr('customers'),
                  value: '${data.customers.length}',
                  icon: Icons.people_alt_rounded,
                  color: AppTheme.accent,
                  onTap: () => widget.onNavigateTab(2),
                ),
                StatCard(
                  label: context.tr('inventory_items'),
                  value:
                      '${data.inventory.length} ${context.tr('types_suffix')}',
                  icon: Icons.inventory_2_rounded,
                  color: AppTheme.success,
                  onTap: () => widget.onNavigateTab(3),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}


import 'dart:convert';
import 'dart:typed_data';

import 'package:audioplayers/audioplayers.dart';
import 'package:file_picker/file_picker.dart';
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

  final void Function(int tabIndex) onNavigateTab;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final AudioService _audio = AudioService();

  bool _isRecording = false;
  bool _isProcessing = false;

  int _processingGeneration = 0;

  final Map<String, int> _recentBookingIds = {};

  @override
  void dispose() {
    _processingGeneration++;
    _audio.dispose();
    super.dispose();
  }

  String _customerKey(String? name) =>
      (name ?? '').trim().toLowerCase();

  Future<void> _startRecording() async {
    try {
      await _audio.startRecording();

      if (!mounted) return;

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

  void _cancelProcessing() {
    if (!_isProcessing) return;

    _processingGeneration++;

    setState(() {
      _isProcessing = false;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Command processing cancelled.'),
      ),
    );
  }


Future<void> _stopRecording() async {
  final requestId = ++_processingGeneration;

  setState(() {
    _isRecording = false;
    _isProcessing = true;
  });

  try {
    final audioBytes = await _audio.stopRecording();

    if (!mounted || requestId != _processingGeneration) return;

    if (audioBytes == null || audioBytes.isEmpty) {
      setState(() => _isProcessing = false);
      return;
    }

    final api = context.read<ApiService>();

    // Save every live microphone recording to the Audio Archive first.
    final archiveFilename =
        'voice_recording_${DateTime.now().millisecondsSinceEpoch}.wav';
    try {
      await api.uploadAudioArchive(
        audioBytes: audioBytes,
        filename: archiveFilename,
      );
    } catch (archiveError) {
      // Archiving should not block the normal voice-processing flow.
      debugPrint('Audio archive save failed: $archiveError');
      if (mounted && requestId == _processingGeneration) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not save recording to archive: $archiveError')),
        );
      }
    }

    if (!mounted || requestId != _processingGeneration) return;

    final result = await api.sendAudioForProcessing(
      audioBytes,
      filename: archiveFilename,
    );

    if (!mounted || requestId != _processingGeneration) return;

    await _handleVoiceResult(result, requestId);
  } catch (e) {
    if (!mounted || requestId != _processingGeneration) return;

    setState(() => _isProcessing = false);

    final message =
        context.tr('could_not_start_recording', listen: false);

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('$message: $e')),
    );
  }
}


Future<void> _handleVoiceResult(
  VoiceParseResult result,
  int requestId,
) async {
  final notUnderstoodMsg =
      context.tr('not_understood_fallback', listen: false);

  if (!mounted || requestId != _processingGeneration) return;

  setState(() => _isProcessing = false);

  if (result.transactions.isEmpty) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(notUnderstoodMsg)),
    );
    return;
  }

  final queryTxns = result.transactions
      .where((t) => t.intent == TransactionIntent.query)
      .toList();

  final actionableTxns = result.transactions
      .where((t) => t.intent != TransactionIntent.query)
      .toList();

  if (queryTxns.isNotEmpty) {
    final api = context.read<ApiService>();
    final transcript = result.rawTranscript.toLowerCase();

    final orderKeywords = [
      'order',
      'à²†à²°à³à²¡à²°à³',
      'book',
      'à²¬à³à²•à³',
      'list',
      'details',
    ];

    final balanceKeywords = [
      'baaki',
      'à²¬à²¾à²•à²¿',
      'balance',
      'estu',
      'à²Žà²·à³à²Ÿà³',
      'owe',
    ];

    final asksAboutOrders =
        orderKeywords.any((k) => transcript.contains(k));

    final asksAboutBalance =
        balanceKeywords.any((k) => transcript.contains(k));

    final wantsOrders = asksAboutOrders && !asksAboutBalance;

    for (final q in queryTxns) {
      if (!mounted || requestId != _processingGeneration) return;

      try {
        if (q.customerName == null) {
          Map<String, dynamic> aggInfo;

          if (q.item != null) {
            aggInfo = await api.getItemStatus(q.item!);
          } else {
            aggInfo = await api.getCustomersWithBalance(
              minAmount: q.amount ?? 0.0,
            );
          }

          if (!mounted || requestId != _processingGeneration) return;

          if (aggInfo.containsKey('error')) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(aggInfo['error'] as String),
              ),
            );
            continue;
          }

          final aggText = aggInfo['spoken_text'] as String;

          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(aggText),
              duration: const Duration(seconds: 6),
            ),
          );

          final aggAudioBase64 =
              aggInfo['audio_base64'] as String?;

          if (aggAudioBase64 != null) {
            try {
              await _audio.playBytes(base64Decode(aggAudioBase64));
            } catch (e) {
              debugPrint('TTS playback failed: $e');
            }
          }

          continue;
        }

        final info = wantsOrders
            ? await api.getOrdersForCustomerName(q.customerName!)
            : await api.getBalanceForCustomerName(q.customerName!);

        if (!mounted || requestId != _processingGeneration) return;

        if (info == null) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                'No customer found matching "${q.customerName}"',
              ),
            ),
          );
          continue;
        }

        final displayText = wantsOrders
            ? (info['spoken_text'] as String)
            : '${info['customer_name']} owes ₹${(info['balance_due'] as num).toStringAsFixed(0)}';

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(displayText),
            duration: const Duration(seconds: 5),
          ),
        );

        final audioBase64 = info['audio_base64'] as String?;

        if (audioBase64 != null) {
          try {
            await _audio.playBytes(base64Decode(audioBase64));
          } catch (e) {
            debugPrint('TTS playback failed: $e');
          }
        }
      } catch (e) {
        if (!mounted || requestId != _processingGeneration) return;

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Could not look up answer: $e'),
          ),
        );
      }
    }
  }

  if (!mounted || requestId != _processingGeneration) return;

  if (actionableTxns.isEmpty) return;

  int? contextualBookingId;

  final paymentCustomers = actionableTxns
      .where((t) => t.intent == TransactionIntent.payment)
      .map((t) => _customerKey(t.customerName))
      .where((name) => name.isNotEmpty)
      .toSet();

  if (paymentCustomers.length == 1) {
    contextualBookingId =
        _recentBookingIds[paymentCustomers.first];
  }

  _showConfirmSheet(
    VoiceParseResult(
      rawTranscript: result.rawTranscript,
      entryTimestamp: result.entryTimestamp,
      transactions: actionableTxns,
      isMultiIntent: actionableTxns.length > 1,
      confidenceNote: result.confidenceNote,
      bookingId: contextualBookingId,
    ),
  );
}


  void _showConfirmSheet(VoiceParseResult result) {
    final api = context.read<ApiService>();
    final appDataProvider = context.read<AppDataProvider>();

    final savedMsg = context.tr('saved_successfully', listen: false);
    final errorMsg =
        context.tr('could_not_start_recording', listen: false);

    final readbackText = _buildReadbackText(result);

    api.synthesizeSpeech(readbackText).then((audioBytes) {
      if (audioBytes != null && mounted) {
        _audio.playBytes(audioBytes);
      }
    });

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
        api: api,
        audio: _audio,
        onConfirm: (finalResult) async {
          try {
            final saveResults =
                await api.saveVoiceResult(finalResult);

            if (!mounted || !sheetContext.mounted) return;

            Navigator.pop(sheetContext);

            final savedBookings =
                (saveResults['bookings'] as List?) ?? [];

            for (final booking in savedBookings) {
              if (booking is Map &&
                  booking['booking_id'] != null &&
                  booking['customer'] != null) {
                _recentBookingIds[
                  _customerKey(booking['customer'] as String)
                ] = (booking['booking_id'] as num).toInt();
              }
            }

            final errors = (saveResults['errors'] as List?) ?? [];

            if (errors.isNotEmpty) {
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

            appDataProvider.refreshFromBackend(api);
          } catch (e) {
            if (!mounted) return;

            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text('$errorMsg: $e'),
                backgroundColor: AppTheme.danger,
              ),
            );

            rethrow;
          }
        },
        onReject: () {
          Navigator.pop(sheetContext);
        },
      ),
    );
  }

  void _openAudioArchive() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(
          top: Radius.circular(24),
        ),
      ),
      builder: (_) => AudioArchiveSheet(
        audio: _audio,
        onProcessAudio: _processUploadedAudio,
      ),
    );
  }

  Future<void> _processUploadedAudio(
    Uint8List audioBytes,
    String filename,
  ) async {
    if (!mounted) return;

    if (_isRecording || _isProcessing) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Finish the current voice command first.'),
        ),
      );
      return;
    }

    final requestId = ++_processingGeneration;

    setState(() => _isProcessing = true);

    try {
      final api = context.read<ApiService>();
      final result = await api.sendAudioForProcessing(
        audioBytes,
        filename: filename,
      );

      if (!mounted || requestId != _processingGeneration) return;

      await _handleVoiceResult(result, requestId);
    } catch (e) {
      if (!mounted || requestId != _processingGeneration) return;

      setState(() => _isProcessing = false);

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Audio was saved to the archive, but processing failed: $e',
          ),
          backgroundColor: AppTheme.danger,
          duration: const Duration(seconds: 6),
        ),
      );
    }
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
            if (_isProcessing) ...[
              const SizedBox(height: 12),
              Center(
                child: OutlinedButton.icon(
                  onPressed: _cancelProcessing,
                  icon: const Icon(
                    Icons.close,
                    color: AppTheme.danger,
                  ),
                  label: const Text(
                    'Cancel processing',
                    style: TextStyle(color: AppTheme.danger),
                  ),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: AppTheme.danger),
                  ),
                ),
              ),
            ],
            const SizedBox(height: 20),

            // Audio archive entry point.
            OutlinedButton.icon(
              onPressed: _openAudioArchive,
              icon: const Icon(Icons.audio_file_rounded),
              label: const Text('Audio Archive'),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 15),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
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

  String _buildReadbackText(VoiceParseResult result) {
    final parts = <String>[];

    for (final txn in result.transactions) {
      switch (txn.intent) {
        case TransactionIntent.booking:
          parts.add(
            '${txn.customerName ?? ""} ಗೆ ${txn.quantity ?? ""} ${txn.item ?? ""} ಬುಕ್ ಆಗಿದೆ',
          );
          break;

        case TransactionIntent.payment:
          parts.add(
            '${txn.customerName ?? ""} ಇಂದು ${txn.amount?.toStringAsFixed(0) ?? ""} rupees payment ಸಿಕ್ಕಿದೆ',
          );
          break;

        case TransactionIntent.returnItem:
          parts.add(
            '${txn.customerName ?? ""} ${txn.quantity ?? ""} ${txn.item ?? ""} ರಿಟರ್ನ್ ಮಾಡಿದ್ದಾರೆ',
          );
          break;

        case TransactionIntent.complete:
          parts.add(
            '${txn.customerName ?? ""} order complete ಆಗಿದೆ',
          );
          break;

        case TransactionIntent.cancel:
          parts.add(
            '${txn.customerName ?? ""} order cancel ಆಗಿದೆ',
          );
          break;

        default:
          break;
      }
    }

    return parts.isEmpty ? '' : '${parts.join(". ")}. ಸರಿನಾ?';
  }
}

class AudioArchiveSheet extends StatefulWidget {
  const AudioArchiveSheet({
    super.key,
    required this.audio,
    required this.onProcessAudio,
  });

  final AudioService audio;
  final Future<void> Function(Uint8List audioBytes, String filename)
      onProcessAudio;

  @override
  State<AudioArchiveSheet> createState() => _AudioArchiveSheetState();
}

class _AudioArchiveSheetState extends State<AudioArchiveSheet> {
  List<Map<String, dynamic>> _recordings = [];
  bool _isLoading = true;
  bool _isUploading = false;
  String? _playingAudioId;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadArchive();
  }

  Future<void> _loadArchive() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final api = context.read<ApiService>();
      final recordings = await api.fetchAudioArchive();

      if (!mounted) return;

      setState(() {
        _recordings = recordings;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }


  Future<void> _uploadAudio() async {
    final api = context.read<ApiService>();

    try {
      final file = await FilePicker.pickFile(
        type: FileType.audio,
      );

      if (file == null || !mounted) return;

      final bytes = await file.readAsBytes();

      if (!mounted) return;

      if (bytes.isEmpty) {
        throw Exception('The selected audio file is empty.');
      }

      setState(() => _isUploading = true);

      await api.uploadAudioArchive(
        audioBytes: bytes,
        filename: file.name,
      );

      if (!mounted) return;

      await _loadArchive();

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Audio saved. Starting voice processing...'),
        ),
      );

      Navigator.of(context).pop();

      await widget.onProcessAudio(bytes, file.name);
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Audio upload failed: $e'),
          backgroundColor: AppTheme.danger,
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _isUploading = false);
      }
    }
  }

  Future<void> _togglePlayback(Map<String, dynamic> recording) async {
    final playbackUrl = recording['playback_url']?.toString();

    if (playbackUrl == null || playbackUrl.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Playback is unavailable for this recording.'),
        ),
      );
      return;
    }

    final id = recording['id']?.toString();
    if (id == null) return;

    try {
      final state = widget.audio.playerState;

      if (_playingAudioId == id) {
        if (state == PlayerState.playing) {
          await widget.audio.pausePlayback();
        } else if (state == PlayerState.paused) {
          await widget.audio.resumePlayback();
        } else {
          await widget.audio.playUrl(playbackUrl);
        }
      } else {
        setState(() => _playingAudioId = id);
        await widget.audio.playUrl(playbackUrl);
      }
    } catch (e) {
      if (!mounted) return;

      setState(() => _playingAudioId = null);

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Could not play audio: $e'),
          backgroundColor: AppTheme.danger,
        ),
      );
    }
  }

  Future<void> _deleteAudio(Map<String, dynamic> recording) async {
    final id = (recording['id'] as num).toInt();

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Delete recording?'),
        content: Text(
          'Delete "${recording['filename']}" permanently?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text(
              'Delete',
              style: TextStyle(color: AppTheme.danger),
            ),
          ),
        ],
      ),
    );

    if (confirmed != true || !mounted) return;

    try {
      await context.read<ApiService>().deleteArchivedAudio(id);

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Recording deleted.')),
      );

      await _loadArchive();
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Could not delete recording: $e'),
          backgroundColor: AppTheme.danger,
        ),
      );
    }
  }

  String _formatDate(dynamic value) {
    if (value == null) return 'Unknown';

    final date = DateTime.tryParse(value.toString())?.toLocal();

    if (date == null) return 'Unknown';

    return '${date.day}/${date.month}/${date.year}';
  }

  String _formatSize(dynamic value) {
    final bytes = (value as num?)?.toDouble() ?? 0;

    if (bytes < 1024) return '${bytes.toInt()} B';
    if (bytes < 1024 * 1024) {
      return '${(bytes / 1024).toStringAsFixed(1)} KB';
    }

    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: SizedBox(
        height: MediaQuery.of(context).size.height * 0.85,
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 20, 12, 12),
              child: Row(
                children: [
                  const Icon(Icons.library_music_rounded, size: 26),
                  const SizedBox(width: 10),
                  const Expanded(
                    child: Text(
                      'Audio Archive',
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  IconButton(
                    onPressed: _loadArchive,
                    icon: const Icon(Icons.refresh_rounded),
                    tooltip: 'Refresh',
                  ),
                  IconButton(
                    onPressed: () => Navigator.pop(context),
                    icon: const Icon(Icons.close_rounded),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: _isUploading ? null : _uploadAudio,
                  icon: _isUploading
                      ? const SizedBox(
                          height: 18,
                          width: 18,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                          ),
                        )
                      : const Icon(Icons.upload_file_rounded),
                  label: Text(
                    _isUploading ? 'Uploading...' : 'Upload audio file',
                  ),
                ),
              ),
            ),
            const Padding(
              padding: EdgeInsets.fromLTRB(20, 12, 20, 8),
              child: Text(
                'Recordings are retained for 20 days and then automatically deleted.',
                style: TextStyle(fontSize: 12),
                textAlign: TextAlign.center,
              ),
            ),
            const Divider(),
            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : _error != null
                      ? Center(
                          child: Padding(
                            padding: const EdgeInsets.all(20),
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                const Icon(
                                  Icons.error_outline,
                                  color: AppTheme.danger,
                                  size: 36,
                                ),
                                const SizedBox(height: 12),
                                Text(
                                  _error!,
                                  textAlign: TextAlign.center,
                                ),
                                const SizedBox(height: 12),
                                OutlinedButton(
                                  onPressed: _loadArchive,
                                  child: const Text('Try again'),
                                ),
                              ],
                            ),
                          ),
                        )
                      : _recordings.isEmpty
                          ? const Center(
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(
                                    Icons.audio_file_outlined,
                                    size: 56,
                                    color: AppTheme.textMuted,
                                  ),
                                  SizedBox(height: 12),
                                  Text('No archived recordings yet.'),
                                  SizedBox(height: 4),
                                  Text(
                                    'Upload an audio file to get started.',
                                    style: TextStyle(
                                      color: AppTheme.textMuted,
                                      fontSize: 12,
                                    ),
                                  ),
                                ],
                              ),
                            )
                          : RefreshIndicator(
                              onRefresh: _loadArchive,
                              child: ListView.separated(
                                padding: const EdgeInsets.all(16),
                                itemCount: _recordings.length,
                                separatorBuilder: (_, __) =>
                                    const SizedBox(height: 10),
                                itemBuilder: (context, index) {
                                  final recording = _recordings[index];

                                  return Card(
                                    child: ListTile(
                                      leading: const CircleAvatar(
                                        child: Icon(Icons.audio_file),
                                      ),
                                      title: Text(
                                        recording['filename']?.toString() ??
                                            'Audio recording',
                                        maxLines: 2,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                      subtitle: Padding(
                                        padding:
                                            const EdgeInsets.only(top: 6),
                                        child: Text(
                                          '${_formatSize(recording['size'])}'
                                          ' • ${_formatDate(recording['created_at'])}\n'
                                          'Expires: ${_formatDate(recording['expires_at'])}',
                                        ),
                                      ),
                                      isThreeLine: true,
                                      trailing: Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          StreamBuilder<PlayerState>(
                                            stream: widget.audio
                                                .playerStateStream,
                                            initialData:
                                                widget.audio.playerState,
                                            builder: (context, snapshot) {
                                              final isThisPlaying =
                                                  _playingAudioId ==
                                                      recording['id']
                                                          ?.toString();
                                              final state =
                                                  snapshot.data ??
                                                      PlayerState.stopped;

                                              final isPlaying =
                                                  isThisPlaying &&
                                                  state == PlayerState.playing;

                                              return IconButton(
                                                onPressed: () =>
                                                    _togglePlayback(recording),
                                                icon: Icon(
                                                  isPlaying
                                                      ? Icons.pause_circle_filled
                                                      : Icons.play_circle_fill,
                                                  size: 30,
                                                  color: AppTheme.accent,
                                                ),
                                                tooltip:
                                                    isPlaying ? 'Pause' : 'Play',
                                              );
                                            },
                                          ),
                                          IconButton(
                                            onPressed: () =>
                                                _deleteAudio(recording),
                                            icon: const Icon(
                                              Icons.delete_outline_rounded,
                                              color: AppTheme.danger,
                                            ),
                                            tooltip: 'Delete recording',
                                          ),
                                        ],
                                      ),
                                    ),
                                  );
                                },
                              ),
                            ),
            ),
          ],
        ),
      ),
    );
  }
}

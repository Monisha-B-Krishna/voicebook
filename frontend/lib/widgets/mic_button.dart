import 'package:flutter/material.dart';
import '../l10n/app_strings.dart';
import '../theme/app_theme.dart';

class MicButton extends StatefulWidget {
  const MicButton({
    super.key,
    required this.isRecording,
    required this.isProcessing,
    required this.onStart,
    required this.onStop,
  });

  final bool isRecording;
  final bool isProcessing;
  final VoidCallback onStart;
  final VoidCallback onStop;

  @override
  State<MicButton> createState() => _MicButtonState();
}

class _MicButtonState extends State<MicButton> with SingleTickerProviderStateMixin {
  late final AnimationController _pulseController;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        GestureDetector(
          onLongPressStart: widget.isProcessing ? null : (_) => widget.onStart(),
          onLongPressEnd: widget.isProcessing ? null : (_) => widget.onStop(),
          onTap: widget.isProcessing
              ? null
              : () {
                  if (widget.isRecording) {
                    widget.onStop();
                  } else {
                    widget.onStart();
                  }
                },
          child: AnimatedBuilder(
            animation: _pulseController,
            builder: (context, child) {
              final scale = widget.isRecording
                  ? 1.0 + (_pulseController.value * 0.12)
                  : 1.0;
              return Transform.scale(scale: scale, child: child);
            },
            child: Container(
              width: 120,
              height: 120,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: widget.isRecording ? AppTheme.danger : AppTheme.primary,
                boxShadow: [
                  BoxShadow(
                    color: (widget.isRecording ? AppTheme.danger : AppTheme.primary)
                        .withOpacity(0.35),
                    blurRadius: 24,
                    spreadRadius: 4,
                  ),
                ],
              ),
              child: widget.isProcessing
                  ? const Padding(
                      padding: EdgeInsets.all(32),
                      child: CircularProgressIndicator(color: Colors.white, strokeWidth: 3),
                    )
                  : Icon(
                      widget.isRecording ? Icons.stop_rounded : Icons.mic_rounded,
                      color: Colors.white,
                      size: 52,
                    ),
            ),
          ),
        ),
        const SizedBox(height: 14),
        Text(
          widget.isProcessing
              ? context.tr('mic_understanding')
              : widget.isRecording
                  ? context.tr('mic_listening')
                  : context.tr('mic_idle'),
          style: TextStyle(
            color: AppTheme.textMuted,
            fontSize: 14,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }
}

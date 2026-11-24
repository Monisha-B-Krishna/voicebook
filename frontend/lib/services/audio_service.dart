import 'dart:async';
import 'dart:typed_data';
import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:record/record.dart';

/// Handles microphone recording and TTS/audio playback.
class AudioService {
  final AudioRecorder _recorder = AudioRecorder();
  final AudioPlayer _player = AudioPlayer();

  bool _isRecording = false;
  bool get isRecording => _isRecording;

  PlayerState get playerState => _player.state;
  Stream<PlayerState> get playerStateStream => _player.onPlayerStateChanged;

  BytesBuilder _audioData = BytesBuilder(copy: false);

  StreamSubscription<Uint8List>? _subscription;
  Completer<void>? _streamDone;

  int _sampleRate = 44100;
  int _numChannels = 1;

  Object? _streamError;

  Future<bool> requestMicPermission() async {
    return await _recorder.hasPermission();
  }

  Future<void> startRecording() async {
    if (_isRecording) return;

    final hasPermission = await requestMicPermission();

    if (!hasPermission) {
      throw Exception('Microphone permission denied');
    }

    _audioData = BytesBuilder(copy: false);
    _streamDone = Completer<void>();
    _streamError = null;

    _sampleRate = 44100;
    _numChannels = 1;

    _recorder.setOnConfigChanged((config) {
      _sampleRate = config.sampleRate;
      _numChannels = config.numChannels;

      debugPrint(
        '[AUDIO] Actual config: '
        '${config.sampleRate} Hz, ${config.numChannels} channel(s)',
      );
    });

    final stream = await _recorder.startStream(
      const RecordConfig(
        encoder: AudioEncoder.pcm16bits,
        sampleRate: 44100,
        numChannels: 1,
      ),
    );

    _subscription = stream.listen(
      (chunk) {
        _audioData.add(chunk);
      },
      onError: (Object error) {
        _streamError = error;

        if (!(_streamDone?.isCompleted ?? true)) {
          _streamDone!.complete();
        }
      },
      onDone: () {
        if (!(_streamDone?.isCompleted ?? true)) {
          _streamDone!.complete();
        }
      },
    );

    _isRecording = true;

    debugPrint('[AUDIO] Recording started');
  }

  Future<Uint8List?> stopRecording() async {
    if (!_isRecording) return null;

    await _recorder.stop();

    if (_streamDone != null) {
      await _streamDone!.future;
    }

    _isRecording = false;

    if (_streamError != null) {
      throw Exception('Microphone stream failed: $_streamError');
    }

    final pcmBytes = _audioData.takeBytes();

    if (pcmBytes.isEmpty) {
      debugPrint('[AUDIO] ERROR: No PCM data captured');
      return null;
    }

    _printAudioDiagnostics(pcmBytes);

    final wavBytes = _createWavFile(
      pcmBytes,
      sampleRate: _sampleRate,
      channels: _numChannels,
    );

    debugPrint('[AUDIO] WAV size: ${wavBytes.length} bytes');

    return wavBytes;
  }

  void _printAudioDiagnostics(Uint8List pcmBytes) {
    const int bytesPerSample = 2;
    final frameSize = bytesPerSample * _numChannels;

    final durationSeconds =
        pcmBytes.length / (_sampleRate * frameSize);

    final data = ByteData.sublistView(pcmBytes);

    double peak = 0;
    double sumSquares = 0;
    int sampleCount = 0;

    for (int offset = 0; offset + 1 < pcmBytes.length; offset += 2) {
      final sample = data.getInt16(offset, Endian.little);
      final normalized = sample / 32768.0;

      peak = math.max(peak, normalized.abs());
      sumSquares += normalized * normalized;
      sampleCount++;
    }

    final rms = sampleCount == 0
        ? 0.0
        : math.sqrt(sumSquares / sampleCount);

    debugPrint('========== AUDIO DIAGNOSTICS ==========');
    debugPrint('[AUDIO] Sample rate: $_sampleRate Hz');
    debugPrint('[AUDIO] Channels: $_numChannels');
    debugPrint('[AUDIO] PCM bytes: ${pcmBytes.length}');
    debugPrint('[AUDIO] Duration: ${durationSeconds.toStringAsFixed(2)} sec');
    debugPrint('[AUDIO] Peak level: ${(peak * 100).toStringAsFixed(2)}%');
    debugPrint('[AUDIO] RMS level: ${(rms * 100).toStringAsFixed(2)}%');
    debugPrint('=======================================');
  }

  Future<void> cancelRecording() async {
    if (!_isRecording) return;

    await _recorder.cancel();

    if (_streamDone != null) {
      await _streamDone!.future;
    }

    await _subscription?.cancel();
    _subscription = null;

    _audioData = BytesBuilder(copy: false);
    _isRecording = false;

    debugPrint('[AUDIO] Recording cancelled');
  }

  Uint8List _createWavFile(
    Uint8List pcmBytes, {
    required int sampleRate,
    required int channels,
  }) {
    const int bitsPerSample = 16;

    final int byteRate =
        sampleRate * channels * bitsPerSample ~/ 8;

    final int blockAlign =
        channels * bitsPerSample ~/ 8;

    final header = ByteData(44);

    void writeString(int offset, String value) {
      for (int i = 0; i < value.length; i++) {
        header.setUint8(offset + i, value.codeUnitAt(i));
      }
    }

    writeString(0, 'RIFF');
    header.setUint32(4, 36 + pcmBytes.length, Endian.little);
    writeString(8, 'WAVE');

    writeString(12, 'fmt ');
    header.setUint32(16, 16, Endian.little);
    header.setUint16(20, 1, Endian.little);
    header.setUint16(22, channels, Endian.little);
    header.setUint32(24, sampleRate, Endian.little);
    header.setUint32(28, byteRate, Endian.little);
    header.setUint16(32, blockAlign, Endian.little);
    header.setUint16(34, bitsPerSample, Endian.little);

    writeString(36, 'data');
    header.setUint32(40, pcmBytes.length, Endian.little);

    final wavBuilder = BytesBuilder(copy: false);

    wavBuilder.add(header.buffer.asUint8List());
    wavBuilder.add(pcmBytes);

    return wavBuilder.takeBytes();
  }

  Future<void> playBytes(List<int> bytes) async {
    await _player.play(
      BytesSource(Uint8List.fromList(bytes)),
    );
  }

  Future<void> playUrl(String url) async {
    await _player.play(UrlSource(url));
  }

  Future<void> pausePlayback() => _player.pause();

  Future<void> resumePlayback() => _player.resume();

  Future<void> stopPlayback() => _player.stop();

  void dispose() {
    _recorder.dispose();
    _player.dispose();
  }
}

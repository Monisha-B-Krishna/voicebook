import 'dart:io';
import 'dart:typed_data';
import 'package:audioplayers/audioplayers.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:record/record.dart';

/// Wraps microphone recording and TTS-audio playback.
/// Mic input -> saved as a local .m4a file -> uploaded to backend.
/// TTS response audio (bytes from backend) -> played back to the owner.
class AudioService {
  final AudioRecorder _recorder = AudioRecorder();
  final AudioPlayer _player = AudioPlayer();

  bool _isRecording = false;
  bool get isRecording => _isRecording;

  Future<bool> requestMicPermission() async {
    final status = await Permission.microphone.request();
    return status.isGranted;
  }

  Future<void> startRecording() async {
    final hasPermission = await requestMicPermission();
    if (!hasPermission) {
      throw Exception('Microphone permission denied');
    }
    final dir = await getTemporaryDirectory();
    final path =
        '${dir.path}/voice_${DateTime.now().millisecondsSinceEpoch}.m4a';

    await _recorder.start(
      const RecordConfig(encoder: AudioEncoder.aacLc),
      path: path,
    );
    _isRecording = true;
  }

  /// Stops recording and returns the path to the saved audio file,
  /// or null if nothing was recorded.
  Future<String?> stopRecording() async {
    final path = await _recorder.stop();
    _isRecording = false;
    return path;
  }

  Future<void> cancelRecording() async {
    if (_isRecording) {
      final path = await _recorder.stop();
      _isRecording = false;
      if (path != null) {
        final f = File(path);
        if (await f.exists()) await f.delete();
      }
    }
  }

  /// Plays a TTS response either from raw bytes (backend) or a local asset.
  Future<void> playBytes(List<int> bytes) async {
    await _player.play(BytesSource(Uint8List.fromList(bytes)));
  }

  Future<void> playUrl(String url) async {
    await _player.play(UrlSource(url));
  }

  void dispose() {
    _recorder.dispose();
    _player.dispose();
  }
}

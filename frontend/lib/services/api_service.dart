
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';

import '../models/voice_transaction.dart';

class ApiService {
  ApiService({String? baseUrl})
      : baseUrl = baseUrl ??
            const String.fromEnvironment(
              'API_BASE_URL',
              defaultValue: 'http://10.159.185.7:8000',
            ),
        _dio = Dio(
          BaseOptions(
            connectTimeout: const Duration(seconds: 8),
            receiveTimeout: const Duration(seconds: 30),
          ),
        );

  final String baseUrl;
  final Dio _dio;
  String? authToken;

  Options get _authOptions => Options(
        headers: authToken == null
            ? null
            : {'Authorization': 'Bearer $authToken'},
      );

  // ---------- Voice processing ----------

  Future<VoiceParseResult> sendAudioForProcessing(
    Uint8List audioBytes, {
    String nluBackend = 'groq',
    String filename = 'voice.wav',
  }) async {
    final formData = FormData.fromMap({
      'file': MultipartFile.fromBytes(
        audioBytes,
        filename: filename,
      ),
    });

    final res = await _dio.post(
      '$baseUrl/voice/process-audio',
      queryParameters: {'backend': nluBackend},
      data: formData,
      options: _authOptions,
    );

    final body = res.data as Map<String, dynamic>;

    if (body['status'] == 'error') {
      throw Exception(body['message'] ?? 'Voice processing failed');
    }

    return VoiceParseResult.fromJson(
      body['result'] as Map<String, dynamic>,
    );
  }

  Future<String> transcribeOnly(Uint8List audioBytes) async {
    final formData = FormData.fromMap({
      'file': MultipartFile.fromBytes(
        audioBytes,
        filename: 'reply.wav',
      ),
    });

    final res = await _dio.post(
      '$baseUrl/voice/transcribe-only',
      data: formData,
      options: _authOptions,
    );

    final body = res.data as Map<String, dynamic>;

    if (body['status'] == 'error') {
      throw Exception(body['message'] ?? 'Transcription failed');
    }

    return body['transcript'] as String;
  }

  // ---------- Audio archive ----------

  Future<Map<String, dynamic>> uploadAudioArchive({
    required Uint8List audioBytes,
    required String filename,
    String? transcript,
    String? language,
  }) async {
    final formData = FormData.fromMap({
      'file': MultipartFile.fromBytes(
        audioBytes,
        filename: filename,
      ),
      if (transcript != null && transcript.trim().isNotEmpty)
        'transcript': transcript,
      if (language != null && language.trim().isNotEmpty)
        'language': language,
    });

    final res = await _dio.post(
      '$baseUrl/audio-archive/',
      data: formData,
      options: _authOptions,
    );

    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<List<Map<String, dynamic>>> fetchAudioArchive() async {
    final res = await _dio.get(
      '$baseUrl/audio-archive/',
      options: _authOptions,
    );

    final body = res.data;

    if (body is List) {
      return List<Map<String, dynamic>>.from(body);
    }

    if (body is Map && body['items'] is List) {
      return List<Map<String, dynamic>>.from(body['items']);
    }

    return [];
  }

  Future<void> deleteArchivedAudio(int audioId) async {
    await _dio.delete(
      '$baseUrl/audio-archive/$audioId',
      options: _authOptions,
    );
  }

  // ---------- Transaction saving ----------

  Future<Map<String, dynamic>> saveVoiceResult(
    VoiceParseResult result,
  ) async {
    final res = await _dio.post(
      '$baseUrl/voice-transactions/',
      data: result.toJson(),
      options: _authOptions,
    );

    final body = res.data as Map<String, dynamic>;

    if (body['status'] == 'error') {
      throw Exception(body['message'] ?? 'Saving transaction failed');
    }

    return body['results'] as Map<String, dynamic>;
  }

  // ---------- Read-only data fetches ----------

  Future<List<Map<String, dynamic>>> fetchCustomers() async {
    final res = await _dio.get(
      '$baseUrl/customers/',
      options: _authOptions,
    );

    return List<Map<String, dynamic>>.from(res.data as List);
  }

  Future<List<Map<String, dynamic>>> fetchInventory() async {
    final res = await _dio.get(
      '$baseUrl/inventory/',
      options: _authOptions,
    );

    return List<Map<String, dynamic>>.from(res.data as List);
  }

  Future<List<Map<String, dynamic>>> fetchBookings() async {
    final res = await _dio.get(
      '$baseUrl/bookings/',
      options: _authOptions,
    );

    return List<Map<String, dynamic>>.from(res.data as List);
  }

  Future<List<Map<String, dynamic>>> fetchPayments() async {
    final res = await _dio.get(
      '$baseUrl/payments/',
      options: _authOptions,
    );

    return List<Map<String, dynamic>>.from(res.data as List);
  }

  Future<dynamic> fetchRaw(String path) async {
    final res = await _dio.get(
      '$baseUrl$path',
      options: _authOptions,
    );

    return res.data;
  }

  // ---------- Customer alias check ----------

  Future<List<Map<String, dynamic>>> checkSimilarCustomers(
    String name,
  ) async {
    final res = await _dio.get(
      '$baseUrl/customers/similar',
      queryParameters: {'name': name},
      options: _authOptions,
    );

    return List<Map<String, dynamic>>.from(res.data as List);
  }

  Future<void> addCustomerAlias(
    int existingCustomerId,
    String aliasName,
  ) async {
    await _dio.post(
      '$baseUrl/customers/$existingCustomerId/aliases',
      data: {'alias_name': aliasName},
      options: _authOptions,
    );
  }

  Future<Map<String, dynamic>?> getBalanceForCustomerName(
    String customerName,
  ) async {
    final customers = await fetchCustomers();

    final match = customers.firstWhere(
      (c) => (c['name'] as String).toLowerCase() ==
          customerName.toLowerCase(),
      orElse: () => {},
    );

    if (match.isEmpty) return null;

    final res = await _dio.get(
      '$baseUrl/customers/${match['customer_id']}/balance',
      options: _authOptions,
    );

    return res.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>?> getOrdersForCustomerName(
    String customerName,
  ) async {
    final customers = await fetchCustomers();

    final match = customers.firstWhere(
      (c) => (c['name'] as String).toLowerCase() ==
          customerName.toLowerCase(),
      orElse: () => {},
    );

    if (match.isEmpty) return null;

    final res = await _dio.get(
      '$baseUrl/customers/${match['customer_id']}/orders',
      options: _authOptions,
    );

    return res.data as Map<String, dynamic>;
  }

  // ---------- Text to speech ----------

  Future<List<int>?> synthesizeSpeech(String text) async {
    try {
      final res = await _dio.post(
        '$baseUrl/tts/synthesize',
        data: {
          'text': text,
          'language_code': 'kn-IN',
        },
        options: _authOptions,
      );

      final body = res.data as Map<String, dynamic>;

      if (body['status'] != 'success') return null;

      return base64Decode(body['audio_base64'] as String);
    } catch (e) {
      return null;
    }
  }

  // ---------- Analytics ----------

  Future<Map<String, dynamic>> getCustomersWithBalance({
    double minAmount = 0.0,
  }) async {
    final res = await _dio.get(
      '$baseUrl/analytics/customers-with-balance',
      queryParameters: {'min_amount': minAmount},
      options: _authOptions,
    );

    return res.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getItemStatus(String itemName) async {
    final res = await _dio.get(
      '$baseUrl/analytics/item-status',
      queryParameters: {'item_name': itemName},
      options: _authOptions,
    );

    return res.data as Map<String, dynamic>;
  }
}

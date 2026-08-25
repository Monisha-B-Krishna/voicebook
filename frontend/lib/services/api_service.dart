import 'package:dio/dio.dart';
import '../models/voice_transaction.dart';

/// Talks to the REAL FastAPI backend. Two endpoints matter for the voice
/// flow specifically:
///
///   POST /voice/process-audio  - uploads recorded audio, backend runs
///                                 Sarvam ASR + NLU, returns a PARSED
///                                 VoiceParseResult. Nothing is saved yet.
///
///   POST /voice-transactions/  - takes a (possibly owner-edited)
///                                 VoiceParseResult and actually saves it:
///                                 resolves customer/item names to real
///                                 database IDs, creates bookings/payments/
///                                 returns, all in one transaction.
///
/// Set [baseUrl] to your backend's address. On an Android emulator talking
/// to a backend running on your own machine, use 10.0.2.2 instead of
/// localhost/127.0.0.1 - the emulator can't see the host machine under
/// that name. On a real phone, use your machine's actual LAN IP address.
class ApiService {
  ApiService({String? baseUrl})
      : baseUrl = baseUrl ?? const String.fromEnvironment(
              'API_BASE_URL',
              defaultValue: 'http://10.0.2.2:8000',
            ),
        _dio = Dio(BaseOptions(
          connectTimeout: const Duration(seconds: 8),
          receiveTimeout: const Duration(seconds: 30),
        ));

  final String baseUrl;
  final Dio _dio;
  String? authToken;

  Options get _authOptions => Options(
        headers: authToken == null ? null : {'Authorization': 'Bearer $authToken'},
      );

  /// Uploads recorded audio to /voice/process-audio and returns the parsed
  /// result. Throws if the backend is unreachable or returns an error -
  /// the caller (home_screen.dart) should catch this and show a clear
  /// message, rather than silently falling back to fake data.
  Future<VoiceParseResult> sendAudioForProcessing(
    String audioFilePath, {
    String nluBackend = 'groq',
  }) async {
    final formData = FormData.fromMap({
      // field name MUST be "file" - matches the backend's
      // `file: UploadFile = File(...)` parameter name exactly.
      'file': await MultipartFile.fromFile(audioFilePath, filename: 'voice.wav'),
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
    return VoiceParseResult.fromJson(body['result'] as Map<String, dynamic>);
  }

  /// Saves a confirmed (possibly owner-edited) VoiceParseResult by calling
  /// /voice-transactions/. Returns the backend's results summary (what was
  /// actually created, and any errors like "item not found in inventory"
  /// or "customer has multiple open bookings") so the UI can show it.
  Future<Map<String, dynamic>> saveVoiceResult(VoiceParseResult result) async {
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

  // ---------- Read-only data fetches (replace AppDataProvider's mock lists) ----------

  Future<List<Map<String, dynamic>>> fetchCustomers() async {
    final res = await _dio.get('$baseUrl/customers/', options: _authOptions);
    return List<Map<String, dynamic>>.from(res.data as List);
  }

  Future<List<Map<String, dynamic>>> fetchInventory() async {
    final res = await _dio.get('$baseUrl/inventory/', options: _authOptions);
    return List<Map<String, dynamic>>.from(res.data as List);
  }

  Future<List<Map<String, dynamic>>> fetchBookings() async {
    final res = await _dio.get('$baseUrl/bookings/', options: _authOptions);
    return List<Map<String, dynamic>>.from(res.data as List);
  }

  Future<List<Map<String, dynamic>>> fetchPayments() async {
    final res = await _dio.get('$baseUrl/payments/', options: _authOptions);
    return List<Map<String, dynamic>>.from(res.data as List);
  }

  /// Generic GET helper for endpoints without a dedicated typed method
  /// above (e.g. /booking-items/, /returns/, /customers/{id}/aliases) -
  /// used by AppDataProvider's client-side joins.
  Future<dynamic> fetchRaw(String path) async {
    final res = await _dio.get('$baseUrl$path', options: _authOptions);
    return res.data;
  }

  // ---------- Customer alias check (matches nlp_alias_check.py's flow) ----------

  /// Checks if [name] is similar to an existing customer. Returns a list
  /// of {customer_id, name, similarity} maps, or an empty list if no
  /// similar match exists. NEVER auto-merges - only suggests, per the
  /// team's decision that alias confirmation must be explicit.
  Future<List<Map<String, dynamic>>> checkSimilarCustomers(String name) async {
    final res = await _dio.get(
      '$baseUrl/customers/similar',
      queryParameters: {'name': name},
      options: _authOptions,
    );
    return List<Map<String, dynamic>>.from(res.data as List);
  }

  /// Records a confirmed alias, AFTER the owner has explicitly confirmed
  /// on screen that [aliasName] refers to the existing customer
  /// [existingCustomerId].
  Future<void> addCustomerAlias(int existingCustomerId, String aliasName) async {
    await _dio.post(
      '$baseUrl/customers/$existingCustomerId/aliases',
      data: {'alias_name': aliasName},
      options: _authOptions,
    );
  }
}

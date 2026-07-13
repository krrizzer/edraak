import 'dart:convert';
import 'package:http/http.dart' as http;

/// Base URLs.
/// - Local dev: pass both explicitly (the Flutter dev server is not the backend):
///     flutter run -d chrome --dart-define=API_BASE=http://localhost:8080 \
///                           --dart-define=GATEWAY_BASE=http://localhost:8081
/// - Production: the app is served by FastAPI, so API_BASE defaults to the same
///   origin, and the gateway URL is fetched at startup from /api/ui-config
///   (driven by the OPENBANKING_GATEWAY_URL env on the backend). No rebuild needed.
class ApiConfig {
  static String? gatewayOverride;

  static String get apiBase {
    const v = String.fromEnvironment('API_BASE');
    return v.isNotEmpty ? v : Uri.base.origin;
  }

  static String get gatewayBase {
    const v = String.fromEnvironment('GATEWAY_BASE');
    if (v.isNotEmpty) return v;
    return gatewayOverride ?? 'http://localhost:8081';
  }
}

class ApiException implements Exception {
  final String message;
  ApiException(this.message);
  @override
  String toString() => message;
}

/// Talks to the Edraak backend and (for consent) directly to the KSAOB gateway.
class Api {
  /// Fetch runtime config (the gateway URL) unless an explicit dart-define wins.
  static Future<void> loadRuntimeConfig() async {
    const explicit = String.fromEnvironment('GATEWAY_BASE');
    if (explicit.isNotEmpty) return;
    try {
      final doc = await _get('${ApiConfig.apiBase}/api/ui-config', '');
      final gw = doc['gateway_base'];
      if (gw is String && gw.isNotEmpty) ApiConfig.gatewayOverride = gw;
    } catch (_) {/* fall back to the localhost default */}
  }

  // ----- Edraak backend -----

  static Future<Map<String, dynamic>> login(String username) =>
      _post('${ApiConfig.apiBase}/api/login', {'username': username}, 'فشل تسجيل الدخول.');

  static Future<Map<String, dynamic>> coverage(String customerId) =>
      _get('${ApiConfig.apiBase}/api/coverage/$customerId', 'تعذر تقييم اكتمال البيانات.');

  /// The smart pre-analyze check: deterministic logic + the AI sufficiency judgment.
  static Future<Map<String, dynamic>> coverageDeep(String customerId) =>
      _get('${ApiConfig.apiBase}/api/coverage/$customerId?deep=true', 'تعذر تقييم اكتمال البيانات.');

  static Future<List<dynamic>> consents(String customerId) =>
      _getList('${ApiConfig.apiBase}/api/consents/$customerId', 'تعذر تحميل الحسابات المرتبطة.');

  static Future<Map<String, dynamic>> ingest(String customerId, String bankCode, String consentId) =>
      _post('${ApiConfig.apiBase}/api/ingest',
          {'customer_id': customerId, 'bank_code': bankCode, 'consent_id': consentId},
          'فشل سحب بيانات البنك.');

  static Future<Map<String, dynamic>> analyze(String customerId, Map<String, dynamic> form) =>
      _post('${ApiConfig.apiBase}/api/analyze', {'customer_id': customerId, ...form}, 'فشل تحليل القرار.');

  static Future<Map<String, dynamic>> radar(String customerId) =>
      _post('${ApiConfig.apiBase}/api/radar/trigger', {'customer_id': customerId}, 'فشل فحص الرادار.');

  static Future<List<dynamic>> alerts(String customerId) =>
      _getList('${ApiConfig.apiBase}/api/alerts/$customerId', 'تعذر تحميل التنبيهات.');

  // ----- KSAOB gateway (separate service, on its own domain) -----

  /// Create a consent (AwaitingAuthorisation) and return {ConsentId, AuthorizeUrl}.
  static Future<Map<String, dynamic>> createConsent(String bankCode, String customerId) async {
    final doc = await _post('${ApiConfig.gatewayBase}/$bankCode/open-banking/v1/consents',
        {'customer_id': customerId}, 'تعذر إنشاء طلب الموافقة.');
    return Map<String, dynamic>.from(doc['Data'] as Map);
  }

  static String authorizeUrl(String bankCode, String consentId) =>
      '${ApiConfig.gatewayBase}/$bankCode/authorize?consent_id=$consentId';

  /// Poll the gateway for the consent's status (Authorised / Rejected / ...).
  static Future<String> consentStatus(String bankCode, String consentId) async {
    final doc = await _get(
        '${ApiConfig.gatewayBase}/$bankCode/open-banking/v1/consents/$consentId', 'تعذر التحقق من الموافقة.');
    return (doc['Data'] as Map)['Status'] as String;
  }

  // ----- helpers -----

  static Future<Map<String, dynamic>> _post(String url, Map<String, dynamic> body, String fallback) async {
    try {
      final r = await http.post(Uri.parse(url),
          headers: {'Content-Type': 'application/json'}, body: jsonEncode(body));
      return _decode(r, fallback);
    } on ApiException {
      rethrow;
    } catch (_) {
      throw ApiException(fallback);
    }
  }

  static Future<Map<String, dynamic>> _get(String url, String fallback) async {
    try {
      final r = await http.get(Uri.parse(url));
      return _decode(r, fallback);
    } on ApiException {
      rethrow;
    } catch (_) {
      throw ApiException(fallback);
    }
  }

  static Future<List<dynamic>> _getList(String url, String fallback) async {
    try {
      final r = await http.get(Uri.parse(url));
      if (r.statusCode >= 400) throw ApiException(fallback);
      return jsonDecode(utf8.decode(r.bodyBytes)) as List<dynamic>;
    } on ApiException {
      rethrow;
    } catch (_) {
      throw ApiException(fallback);
    }
  }

  static Map<String, dynamic> _decode(http.Response r, String fallback) {
    final decoded = r.body.isEmpty ? {} : jsonDecode(utf8.decode(r.bodyBytes));
    if (r.statusCode >= 400) {
      final detail = decoded is Map ? decoded['detail'] ?? decoded['error'] : null;
      throw ApiException(detail is String ? detail : fallback);
    }
    return Map<String, dynamic>.from(decoded as Map);
  }
}

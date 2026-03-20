enum AppRole { admin, engineer }

class AuthStore {
  AuthStore._();

  static String? accessToken;
  static String? refreshToken;
  static String? username;
  static AppRole? role;

  static bool get isLoggedIn => accessToken != null;

  static Map<String, String> authHeaders() {
    final token = accessToken;
    if (token == null) return {};
    return {'Authorization': 'Bearer $token'};
  }

  static void clear() {
    accessToken = null;
    refreshToken = null;
    username = null;
    role = null;
  }
}

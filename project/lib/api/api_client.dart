import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../models.dart';
import 'api_config.dart';
import 'auth_store.dart';

class ApiClient {
  ApiClient._();

  static Uri _uri(String path) => Uri.parse('$apiBaseUrl$path');

  static Future<void> login({required String username, required String password, required AppRole role}) async {
    final res = await http.post(
      _uri('/api/auth/token/'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'username': username, 'password': password}),
    );
    if (res.statusCode != 200) {
      throw Exception('Login failed (${res.statusCode})');
    }
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    AuthStore.accessToken = data['access'] as String?;
    AuthStore.refreshToken = data['refresh'] as String?;
    AuthStore.username = username;
    AuthStore.role = role;
  }

  static Future<Map<String, dynamic>> fetchMe() async {
    final res = await http.get(_uri('/api/me/'), headers: AuthStore.authHeaders());
    if (res.statusCode != 200) {
      throw Exception('Failed to load profile (${res.statusCode})');
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  static Future<void> changePassword({required String oldPassword, required String newPassword}) async {
    final res = await http.post(
      _uri('/api/change-password/'),
      headers: {'Content-Type': 'application/json', ...AuthStore.authHeaders()},
      body: jsonEncode({'old_password': oldPassword, 'new_password': newPassword}),
    );
    if (res.statusCode != 204) {
      String detail = '';
      try {
        final body = jsonDecode(res.body) as Map<String, dynamic>;
        detail = body['detail']?.toString() ?? '';
      } catch (_) {}
      final suffix = detail.isEmpty ? '' : ': $detail';
      throw Exception('Failed to change password (${res.statusCode})$suffix');
    }
  }

  static Future<List<AppTicket>> fetchTickets() async {
    final res = await http.get(_uri('/api/tickets/'), headers: AuthStore.authHeaders());
    if (res.statusCode != 200) {
      throw Exception('Failed to load tickets (${res.statusCode})');
    }
    final list = jsonDecode(res.body) as List<dynamic>;
    return list.map((e) => AppTicket.fromApi(e as Map<String, dynamic>)).toList();
  }

  static Future<List<EngineerProfile>> fetchEngineers() async {
    final res = await http.get(_uri('/api/engineers/'), headers: AuthStore.authHeaders());
    if (res.statusCode != 200) {
      throw Exception('Failed to load engineers (${res.statusCode})');
    }
    final list = jsonDecode(res.body) as List<dynamic>;
    return list.map((e) => EngineerProfile.fromApi(e as Map<String, dynamic>)).toList();
  }

  static Future<List<Customer>> fetchCustomers() async {
    final res = await http.get(_uri('/api/customers/'), headers: AuthStore.authHeaders());
    if (res.statusCode != 200) {
      throw Exception('Failed to load customers (${res.statusCode})');
    }
    final list = jsonDecode(res.body) as List<dynamic>;
    return list.map((e) => Customer.fromApi(e as Map<String, dynamic>)).toList();
  }

  static Future<AppTicket> createTicket({
    required String customerName,
    required String customerPhone,
    required String customerAddress,
    required String location,
    required String issue,
    required String model,
    String? serialNumber,
    String? mfgDate,
  }) async {
    final body = <String, dynamic>{
      'ticket_id': _generateTicketId(),
      'customer_name': customerName,
      'customer_phone': customerPhone,
      'customer_address': customerAddress,
      'location': location,
      'issue': issue,
      'model': model,
    };
    if (serialNumber != null && serialNumber.isNotEmpty) body['serial_number'] = serialNumber;
    if (mfgDate != null && mfgDate.isNotEmpty) body['mfg_date'] = mfgDate;
    final res = await http.post(
      _uri('/api/tickets/'),
      headers: {'Content-Type': 'application/json', ...AuthStore.authHeaders()},
      body: jsonEncode(body),
    );
    if (res.statusCode != 201) {
      throw Exception('Failed to create ticket (${res.statusCode})');
    }
    return AppTicket.fromApi(jsonDecode(res.body) as Map<String, dynamic>);
  }

  static Future<AppTicket> assignTicket({required int ticketId, required int engineerId}) async {
    final res = await http.patch(
      _uri('/api/tickets/$ticketId/'),
      headers: {'Content-Type': 'application/json', ...AuthStore.authHeaders()},
      body: jsonEncode({'assigned_engineer': engineerId, 'status': 'ASSIGNED'}),
    );
    if (res.statusCode != 200) {
      throw Exception('Failed to assign ticket (${res.statusCode})');
    }
    return AppTicket.fromApi(jsonDecode(res.body) as Map<String, dynamic>);
  }

  static Future<void> startTicket({required int ticketId}) async {
    final res = await http.post(_uri('/api/tickets/$ticketId/start/'), headers: AuthStore.authHeaders());
    if (res.statusCode != 200) {
      String detail = '';
      try {
        final body = jsonDecode(res.body) as Map<String, dynamic>;
        detail = body['detail']?.toString() ?? '';
      } catch (_) {}
      final suffix = detail.isEmpty ? '' : ': $detail';
      throw Exception('Failed to start ticket (${res.statusCode})$suffix');
    }
  }

  static Future<ReportData> completeTicket({
    required int ticketId,
    required int numberOfFans,
    required String serialNumber,
    required String problemIdentified,
    required String actionTaken,
    required String pcbBoardNumber,
    required String comments,
    required String chargesCollected,
    required String kmsDriven,
    required bool isCustomerPolite,
    required bool difficultToAttend,
  }) async {
    final res = await http.post(
      _uri('/api/tickets/$ticketId/complete/'),
      headers: {'Content-Type': 'application/json', ...AuthStore.authHeaders()},
      body: jsonEncode({
        'service_provider_code': AuthStore.username ?? '',
        'number_of_fans': numberOfFans,
        'serial_number': serialNumber,
        'problem_identified': problemIdentified,
        'action_taken': actionTaken,
        'pcb_board_number': pcbBoardNumber,
        'comments': comments,
        'charges_collected': chargesCollected,
        'kms_driven': kmsDriven,
        'is_customer_polite': isCustomerPolite,
        'difficult_to_attend': difficultToAttend,
      }),
    );
    if (res.statusCode != 201) {
      throw Exception('Failed to complete ticket (${res.statusCode})');
    }
    return ReportData.fromApi(jsonDecode(res.body) as Map<String, dynamic>);
  }

  static Future<List<ReportData>> fetchReports() async {
    final res = await http.get(_uri('/api/reports/'), headers: AuthStore.authHeaders());
    if (res.statusCode != 200) {
      throw Exception('Failed to load reports (${res.statusCode})');
    }
    final list = jsonDecode(res.body) as List<dynamic>;
    return list.map((e) => ReportData.fromApi(e as Map<String, dynamic>)).toList();
  }

  static Future<Uint8List> fetchReportPdf(int reportId) async {
    final res = await http.get(_uri('/api/reports/$reportId/pdf/'), headers: AuthStore.authHeaders());
    if (res.statusCode != 200) {
      throw Exception('Failed to download PDF (${res.statusCode})');
    }
    return res.bodyBytes;
  }

  static Future<EngineerProfile> createEngineer({
    required String username,
    required String password,
    required String phone,
    required String name,
  }) async {
    final res = await http.post(
      _uri('/api/engineers/'),
      headers: {'Content-Type': 'application/json', ...AuthStore.authHeaders()},
      body: jsonEncode({
        'username': username,
        'password': password,
        'phone': phone,
        'name': name,
        'active': true,
      }),
    );
    if (res.statusCode != 201) {
      throw Exception('Failed to create engineer (${res.statusCode})');
    }
    return EngineerProfile.fromApi(jsonDecode(res.body) as Map<String, dynamic>);
  }

  static Future<EngineerProfile> updateEngineer({
    required int id,
    String? phone,
    String? name,
    String? password,
    bool? active,
  }) async {
    final body = <String, dynamic>{};
    if (phone != null) body['phone'] = phone;
    if (name != null) body['name'] = name;
    if (password != null && password.isNotEmpty) body['password'] = password;
    if (active != null) body['active'] = active;

    final res = await http.patch(
      _uri('/api/engineers/$id/'),
      headers: {'Content-Type': 'application/json', ...AuthStore.authHeaders()},
      body: jsonEncode(body),
    );
    if (res.statusCode != 200) {
      throw Exception('Failed to update engineer (${res.statusCode})');
    }
    return EngineerProfile.fromApi(jsonDecode(res.body) as Map<String, dynamic>);
  }

  static Future<Customer> createCustomer({
    required String name,
    required String address,
    required String contactName,
    required String contactPhone,
  }) async {
    final res = await http.post(
      _uri('/api/customers/'),
      headers: {'Content-Type': 'application/json', ...AuthStore.authHeaders()},
      body: jsonEncode({
        'name': name,
        'address': address,
        'contact_name': contactName,
        'contact_phone': contactPhone,
        'active': true,
      }),
    );
    if (res.statusCode != 201) {
      throw Exception('Failed to create customer (${res.statusCode})');
    }
    return Customer.fromApi(jsonDecode(res.body) as Map<String, dynamic>);
  }

  static Future<Customer> updateCustomer({
    required int id,
    String? name,
    String? address,
    String? contactName,
    String? contactPhone,
    bool? active,
  }) async {
    final body = <String, dynamic>{};
    if (name != null) body['name'] = name;
    if (address != null) body['address'] = address;
    if (contactName != null) body['contact_name'] = contactName;
    if (contactPhone != null) body['contact_phone'] = contactPhone;
    if (active != null) body['active'] = active;

    final res = await http.patch(
      _uri('/api/customers/$id/'),
      headers: {'Content-Type': 'application/json', ...AuthStore.authHeaders()},
      body: jsonEncode(body),
    );
    if (res.statusCode != 200) {
      throw Exception('Failed to update customer (${res.statusCode})');
    }
    return Customer.fromApi(jsonDecode(res.body) as Map<String, dynamic>);
  }

  static String _generateTicketId() {
    final now = DateTime.now();
    return 'TKT-${now.millisecondsSinceEpoch}';
  }
}


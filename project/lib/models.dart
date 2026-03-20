enum TicketStatus { open, assigned, inProgress, completed }

class AppTicket {
  AppTicket({
    required this.id,
    required this.ticketId,
    required this.customerId,
    required this.customerName,
    required this.customerPhone,
    required this.customerAddress,
    required this.location,
    required this.issue,
    required this.model,
    this.serialNumber,
    this.mfgDate,
    required this.status,
    this.engineerId,
    this.engineerName,
    required this.createdAt,
    this.createdByName,
    this.assignedAt,
    this.startedAt,
    this.completedAt,
    this.qrCode,
  });

  final int id;
  final String ticketId;
  final int customerId;
  final String customerName;
  final String customerPhone;
  final String customerAddress;
  final String location;
  final String issue;
  final String model;
  final String? serialNumber;
  final DateTime? mfgDate;
  TicketStatus status;
  int? engineerId;
  String? engineerName;
  final DateTime createdAt;
  final String? createdByName;
  DateTime? assignedAt;
  DateTime? startedAt;
  DateTime? completedAt;
  String? qrCode;

  factory AppTicket.fromApi(Map<String, dynamic> json) {
    return AppTicket(
      id: json['id'] as int,
      ticketId: json['ticket_id'] as String,
      customerId: json['customer'] as int,
      customerName: (json['customer_name'] ?? '') as String,
      customerPhone: (json['customer_phone'] ?? '') as String,
      customerAddress: (json['customer_address'] ?? '') as String,
      location: (json['location'] ?? '') as String,
      issue: (json['issue'] ?? '') as String,
      model: (json['model'] ?? '') as String,
      serialNumber: json['serial_number'] as String?,
      mfgDate: _parseDate(json['mfg_date']),
      status: ticketStatusFromApi((json['status'] ?? 'OPEN') as String),
      engineerId: json['assigned_engineer'] as int?,
      engineerName: json['assigned_engineer_name'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      createdByName: json['created_by_name'] as String?,
      assignedAt: _parseDate(json['assigned_at']),
      startedAt: _parseDate(json['started_at']),
      completedAt: _parseDate(json['completed_at']),
      qrCode: json['qr_code'] as String?,
    );
  }
}

class ReportData {
  ReportData({
    required this.id,
    required this.ticketId,
    required this.engineerName,
    required this.ticketCreatedAt,
    required this.ticketStartedAt,
    required this.ticketCompletedAt,
    required this.serviceProviderCode,
    required this.numberOfFans,
    required this.serialNumber,
    required this.problemIdentified,
    required this.actionTaken,
    required this.pcbBoardNumber,
    required this.comments,
    required this.chargesCollected,
    required this.kmsDriven,
    required this.isCustomerPolite,
    required this.difficultToAttend,
    required this.createdAt,
  });

  final int id;
  final String ticketId;
  final String engineerName;
  final DateTime ticketCreatedAt;
  final DateTime? ticketStartedAt;
  final DateTime? ticketCompletedAt;
  final String serviceProviderCode;
  final int numberOfFans;
  final String serialNumber;
  final String problemIdentified;
  final String actionTaken;
  final String pcbBoardNumber;
  final String comments;
  final String chargesCollected;
  final int kmsDriven;
  final bool isCustomerPolite;
  final bool difficultToAttend;
  final DateTime createdAt;

  factory ReportData.fromApi(Map<String, dynamic> json) {
    return ReportData(
      id: json['id'] as int,
      ticketId: json['ticket_id'] as String,
      engineerName: (json['engineer_name'] ?? '') as String,
      ticketCreatedAt: DateTime.parse(json['ticket_created_at'] as String),
      ticketStartedAt: _parseDate(json['ticket_started_at']),
      ticketCompletedAt: _parseDate(json['ticket_completed_at']),
      serviceProviderCode: (json['service_provider_code'] ?? '') as String,
      numberOfFans: (json['number_of_fans'] ?? 0) as int,
      serialNumber: (json['serial_number'] ?? '') as String,
      problemIdentified: (json['problem_identified'] ?? '') as String,
      actionTaken: (json['action_taken'] ?? '') as String,
      pcbBoardNumber: (json['pcb_board_number'] ?? '') as String,
      comments: (json['comments'] ?? '') as String,
      chargesCollected: (json['charges_collected'] ?? '').toString(),
      kmsDriven: (json['kms_driven'] ?? 0) as int,
      isCustomerPolite: (json['is_customer_polite'] ?? false) as bool,
      difficultToAttend: (json['difficult_to_attend'] ?? false) as bool,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}

class EngineerProfile {
  EngineerProfile({
    required this.id,
    required this.username,
    required this.firstName,
    required this.lastName,
    required this.phone,
    required this.active,
  });

  final int id;
  final String username;
  final String firstName;
  final String lastName;
  final String phone;
  final bool active;

  String get displayName {
    final name = [firstName, lastName].where((s) => s.trim().isNotEmpty).join(' ');
    return name.isEmpty ? username : name;
  }

  factory EngineerProfile.fromApi(Map<String, dynamic> json) {
    final user = (json['user'] ?? {}) as Map<String, dynamic>;
    return EngineerProfile(
      id: json['id'] as int,
      username: (user['username'] ?? '') as String,
      firstName: (user['first_name'] ?? '') as String,
      lastName: (user['last_name'] ?? '') as String,
      phone: (json['phone'] ?? '') as String,
      active: (json['active'] ?? true) as bool,
    );
  }
}

class Customer {
  Customer({
    required this.id,
    required this.name,
    required this.address,
    required this.contactName,
    required this.contactPhone,
    required this.active,
  });

  final int id;
  final String name;
  final String address;
  final String contactName;
  final String contactPhone;
  final bool active;

  factory Customer.fromApi(Map<String, dynamic> json) {
    return Customer(
      id: json['id'] as int,
      name: (json['name'] ?? '') as String,
      address: (json['address'] ?? '') as String,
      contactName: (json['contact_name'] ?? '') as String,
      contactPhone: (json['contact_phone'] ?? '') as String,
      active: (json['active'] ?? true) as bool,
    );
  }
}

TicketStatus ticketStatusFromApi(String value) {
  switch (value) {
    case 'ASSIGNED':
      return TicketStatus.assigned;
    case 'IN_PROGRESS':
      return TicketStatus.inProgress;
    case 'COMPLETED':
      return TicketStatus.completed;
    default:
      return TicketStatus.open;
  }
}

String ticketStatusToApi(TicketStatus status) {
  switch (status) {
    case TicketStatus.assigned:
      return 'ASSIGNED';
    case TicketStatus.inProgress:
      return 'IN_PROGRESS';
    case TicketStatus.completed:
      return 'COMPLETED';
    case TicketStatus.open:
      return 'OPEN';
  }
}

DateTime? _parseDate(dynamic value) {
  if (value == null) return null;
  return DateTime.tryParse(value as String);
}

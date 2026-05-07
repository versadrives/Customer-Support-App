import '../models.dart';

class DemoStore {
  DemoStore._();

  static final engineers = ['Arun K', 'Meera S', 'Rakesh P'];
  static final customers = ['ABC Industries', 'Nova Pumps', 'Sigma Foods'];
  static final tickets = <AppTicket>[
    AppTicket(
      id: 1,
      ticketId: 'TKT-1001',
      customerId: 1,
      customerName: 'ABC Industries',
      customerPhone: '9876543210',
      customerAddress: 'Chennai, TN',
      location: 'Chennai Unit 2',
      issue: 'Motor overheating alert',
      issueNotes: 'Trips specifically after 20 minutes of use.',
      model: 'MX-200',
      serialNumber: 'MX200-7781',
      mfgDate: DateTime(2024, 3, 12),
      purchaseDate: DateTime(2024, 5, 1),
      newFanComplaint: true,
      repeatedComplaintCount: 1,
      status: TicketStatus.assigned,
      engineerName: 'Arun K',
      createdAt: DateTime.now().subtract(const Duration(hours: 7)),
    ),
    AppTicket(
      id: 2,
      ticketId: 'TKT-1002',
      customerId: 2,
      customerName: 'Nova Pumps',
      customerPhone: '9988776655',
      customerAddress: 'Bangalore, KA',
      location: 'Bangalore Plant',
      issue: 'Unexpected vibration',
      issueNotes: 'Happens mostly on higher speed setting.',
      model: 'VP-90',
      serialNumber: 'VP90-2210',
      mfgDate: DateTime(2023, 11, 2),
      purchaseDate: DateTime(2024, 1, 18),
      newFanComplaint: false,
      repeatedComplaintCount: 2,
      status: TicketStatus.inProgress,
      engineerName: 'Meera S',
      createdAt: DateTime.now().subtract(const Duration(hours: 5)),
      startedAt: DateTime.now().subtract(const Duration(hours: 2)),
    ),
    AppTicket(
      id: 3,
      ticketId: 'TKT-1003',
      customerId: 3,
      customerName: 'Sigma Foods',
      customerPhone: '9123456780',
      customerAddress: 'Hyderabad, TS',
      location: 'Hyderabad Warehouse',
      issue: 'Controller fault code E17',
      issueNotes: '',
      model: 'CTRL-7X',
      newFanComplaint: false,
      status: TicketStatus.open,
      createdAt: DateTime.now().subtract(const Duration(hours: 1)),
    ),
  ];

  static final reports = <ReportData>[];

  static int countByStatus(TicketStatus s) => tickets.where((t) => t.status == s).length;
}


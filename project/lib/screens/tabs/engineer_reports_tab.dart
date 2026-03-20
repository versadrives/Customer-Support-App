import 'package:flutter/material.dart';

import '../../api/api_client.dart';
import '../../models.dart';

class EngineerReportsTab extends StatefulWidget {
  const EngineerReportsTab({super.key, required this.engineerName});
  final String engineerName;

  @override
  State<EngineerReportsTab> createState() => _EngineerReportsTabState();
}

class _EngineerReportsTabState extends State<EngineerReportsTab> {
  late Future<List<ReportData>> _future;

  String _fmt(DateTime? value) {
    if (value == null) return '-';
    final v = value.toLocal();
    return '${v.year}-${v.month.toString().padLeft(2, '0')}-${v.day.toString().padLeft(2, '0')} ${v.hour.toString().padLeft(2, '0')}:${v.minute.toString().padLeft(2, '0')}';
  }

  @override
  void initState() {
    super.initState();
    _future = ApiClient.fetchReports();
  }

  Future<void> _refresh() async {
    setState(() => _future = ApiClient.fetchReports());
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<ReportData>>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return Center(child: Text('Failed to load reports. ${snapshot.error}'));
        }
        final myReports = snapshot.data ?? [];
        if (myReports.isEmpty) return const Center(child: Text('No reports submitted yet.'));

        return RefreshIndicator(
          onRefresh: _refresh,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 6, 16, 16),
            children: [
              const Text('My Reports', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
              const SizedBox(height: 4),
              const Text('Compact table view for quick scanning.', style: TextStyle(color: Color(0xFF6B7B8A))),
              const SizedBox(height: 10),
              Align(
                alignment: Alignment.centerRight,
                child: IconButton(onPressed: _refresh, icon: const Icon(Icons.refresh)),
              ),
              const SizedBox(height: 8),
              Container(
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(18),
                  border: Border.all(color: const Color(0xFFE2E8F0)),
                  boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.06), blurRadius: 18, offset: const Offset(0, 10))],
                ),
                padding: const EdgeInsets.all(10),
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: DataTable(
                    columns: const [
                      DataColumn(label: Text('S.No')),
                      DataColumn(label: Text('Log Date')),
                      DataColumn(label: Text('Service Provider Code')),
                      DataColumn(label: Text('Ticket No')),
                      DataColumn(label: Text('Attended By')),
                      DataColumn(label: Text('No. of Fans')),
                      DataColumn(label: Text('Serial No')),
                      DataColumn(label: Text('Problem Identified')),
                      DataColumn(label: Text('Action Taken')),
                      DataColumn(label: Text('PCB Board')),
                      DataColumn(label: Text('Comments')),
                      DataColumn(label: Text('Charges')),
                      DataColumn(label: Text('KM Driven')),
                      DataColumn(label: Text('Customer Polite')),
                      DataColumn(label: Text('Difficult To Attend')),
                    ],
                    rows: [
                      for (var i = 0; i < myReports.length; i++)
                        DataRow(
                          cells: [
                            DataCell(Text('${i + 1}')),
                            DataCell(Text(_fmt(myReports[i].createdAt))),
                            DataCell(Text(myReports[i].serviceProviderCode)),
                            DataCell(Text(myReports[i].ticketId)),
                            DataCell(Text(myReports[i].engineerName)),
                            DataCell(Text('${myReports[i].numberOfFans}')),
                            DataCell(Text(myReports[i].serialNumber)),
                            DataCell(Text(myReports[i].problemIdentified)),
                            DataCell(Text(myReports[i].actionTaken)),
                            DataCell(Text(myReports[i].pcbBoardNumber)),
                            DataCell(Text(myReports[i].comments)),
                            DataCell(Text(myReports[i].chargesCollected)),
                            DataCell(Text('${myReports[i].kmsDriven}')),
                            DataCell(Text(myReports[i].isCustomerPolite ? 'Yes' : 'No')),
                            DataCell(Text(myReports[i].difficultToAttend ? 'Yes' : 'No')),
                          ],
                        ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../../api/api_client.dart';
import '../../models.dart';
import '../../utils/download_helper.dart';

class EngineerReportsTab extends StatefulWidget {
  const EngineerReportsTab({super.key, required this.engineerName});
  final String engineerName;

  @override
  State<EngineerReportsTab> createState() => _EngineerReportsTabState();
}

class _EngineerReportsTabState extends State<EngineerReportsTab> {
  late Future<List<ReportData>> _future;
  DateTime _selectedDate = DateTime.now();
  List<ReportData> _myReports = [];

  String _fmt(DateTime? value) {
    if (value == null) return '-';
    final v = value.toLocal();
    return '${v.year}-${v.month.toString().padLeft(2, '0')}-${v.day.toString().padLeft(2, '0')} ${v.hour.toString().padLeft(2, '0')}:${v.minute.toString().padLeft(2, '0')}';
  }

  String _fmtDate(DateTime value) {
    final v = value.toLocal();
    return '${v.year}-${v.month.toString().padLeft(2, '0')}-${v.day.toString().padLeft(2, '0')}';
  }

  @override
  void initState() {
    super.initState();
    _future = ApiClient.fetchReports(date: _fmtDate(_selectedDate));
  }

  Future<void> _refresh() async {
    setState(() {
      _future = ApiClient.fetchReports(date: _fmtDate(_selectedDate));
    });
    await _future;
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _selectedDate,
      firstDate: DateTime(2023),
      lastDate: DateTime.now(),
    );
    if (picked == null) return;
    setState(() {
      _selectedDate = picked;
      _future = ApiClient.fetchReports(date: _fmtDate(_selectedDate));
    });
  }

  String _toCsv(List<ReportData> reports) {
    final header = [
      'Log Date',
      'Service Provider Code',
      'Ticket No',
      'Attended By',
      'Serial No',
      'Problem Identified',
      'Action Taken',
      'PCB Board',
      'Comments',
      'Charges',
      'KM Driven',
      'Customer Polite',
      'Difficult To Attend',
    ];
    final rows = reports.map((r) {
      return [
        _fmt(r.createdAt),
        r.serviceProviderCode,
        r.ticketId,
        r.engineerName,
        r.serialNumber,
        r.problemIdentified,
        r.actionTaken,
        r.pcbBoardNumber,
        r.comments,
        r.chargesCollected,
        '${r.kmsDriven}',
        r.isCustomerPolite ? 'Yes' : 'No',
        r.difficultToAttend ? 'Yes' : 'No',
      ];
    }).toList();

    String esc(String v) => '"${v.replaceAll('"', '""')}"';
    final lines = <String>[
      header.map(esc).join(','),
      ...rows.map((r) => r.map((v) => esc(v)).join(',')),
    ];
    return lines.join('\n');
  }

  Future<void> _export() async {
    if (_myReports.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('No reports to export.')));
      return;
    }
    try {
      final csv = _toCsv(_myReports);
      final bytes = Uint8List.fromList(csv.codeUnits);
      final filename = 'reports_${_fmtDate(_selectedDate)}.csv';
      final path = await downloadBytes(bytes, filename);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Saved: $path')));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Export failed. $e')));
    }
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
        _myReports = snapshot.data ?? [];
        final myReports = _myReports;

        return RefreshIndicator(
          onRefresh: _refresh,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 6, 16, 16),
            children: [
              const Text('My Reports', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
              const SizedBox(height: 4),
              const Text('Compact table view for quick scanning.', style: TextStyle(color: Color(0xFF6B7B8A))),
              const SizedBox(height: 10),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  OutlinedButton.icon(
                    onPressed: _pickDate,
                    icon: const Icon(Icons.date_range),
                    label: Text(_fmtDate(_selectedDate)),
                  ),
                  Row(
                    children: [
                      IconButton(tooltip: 'Refresh', onPressed: _refresh, icon: const Icon(Icons.refresh)),
                      IconButton(tooltip: 'Export CSV', onPressed: _export, icon: const Icon(Icons.download)),
                    ],
                  ),
                ],
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


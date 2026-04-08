import 'package:flutter/material.dart';

import '../../api/api_client.dart';
import '../../models.dart';
import '../../utils/download_helper.dart';
import '../../widgets/panel.dart';

class AdminReportsTab extends StatefulWidget {
  const AdminReportsTab({super.key, required this.onRefresh});
  final VoidCallback onRefresh;

  @override
  State<AdminReportsTab> createState() => _AdminReportsTabState();
}

class _AdminReportsTabState extends State<AdminReportsTab> {
  late Future<List<ReportData>> _future;

  String _fmt(DateTime? value) {
    if (value == null) return '-';
    return value.toLocal().toString();
  }

  @override
  void initState() {
    super.initState();
    _future = ApiClient.fetchReports();
  }

  Future<void> _refresh() async {
    setState(() => _future = ApiClient.fetchReports());
    await _future;
    widget.onRefresh();
  }

  Future<void> _download(ReportData report) async {
    try {
      final bytes = await ApiClient.fetchReportPdf(report.id);
      await downloadBytes(bytes, 'report_${report.ticketId}.pdf');
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Download failed. $e')));
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
        final reports = snapshot.data ?? [];
        if (reports.isEmpty) return const Center(child: Text('No reports submitted yet.'));

        return ListView(
          padding: const EdgeInsets.fromLTRB(16, 6, 16, 16),
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('All service reports', style: TextStyle(color: Color(0xFF5A6E7A))),
                IconButton(onPressed: _refresh, icon: const Icon(Icons.refresh)),
              ],
            ),
            const SizedBox(height: 8),
            ...reports.map(
              (r) => Panel(
                title: 'Report ${r.ticketId}',
                icon: Icons.task,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Engineer: ${r.engineerName}'),
                    const SizedBox(height: 4),
                    Text('Log Date: ${_fmt(r.createdAt)}'),
                    const SizedBox(height: 4),
                    Text('Ticket Created: ${_fmt(r.ticketCreatedAt)}'),
                    const SizedBox(height: 4),
                    Text('Ticket Started: ${_fmt(r.ticketStartedAt)}'),
                    const SizedBox(height: 4),
                    Text('Ticket Completed: ${_fmt(r.ticketCompletedAt)}'),
                    const SizedBox(height: 4),
                    Text('Service Provider Code: ${r.serviceProviderCode}'),
                    const SizedBox(height: 4),
                    Text('Serial Number: ${r.serialNumber}'),
                    const SizedBox(height: 4),
                    Text('Problem Identified: ${r.problemIdentified}'),
                    const SizedBox(height: 4),
                    Text('Action Taken: ${r.actionTaken}'),
                    const SizedBox(height: 4),
                    Text('PCB Board Number: ${r.pcbBoardNumber}'),
                    const SizedBox(height: 4),
                    Text('Comments: ${r.comments}'),
                    const SizedBox(height: 4),
                    Text('Charges Collected: ${r.chargesCollected}'),
                    const SizedBox(height: 4),
                    Text('KM\'s Driven: ${r.kmsDriven}'),
                    const SizedBox(height: 4),
                    Text('Customer Polite: ${r.isCustomerPolite ? 'Yes' : 'No'}'),
                    const SizedBox(height: 4),
                    Text('Difficult to Attend: ${r.difficultToAttend ? 'Yes' : 'No'}'),
                    const SizedBox(height: 8),
                    Align(
                      alignment: Alignment.centerRight,
                      child: FilledButton.icon(
                        onPressed: () => _download(r),
                        icon: const Icon(Icons.download),
                        label: const Text('Download PDF'),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        );
      },
    );
  }
}


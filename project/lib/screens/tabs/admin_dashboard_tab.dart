import 'package:flutter/material.dart';

import '../../api/api_client.dart';
import '../../models.dart';
import '../../widgets/metric_card.dart';
import '../../widgets/ticket_card.dart';

class AdminDashboardTab extends StatefulWidget {
  const AdminDashboardTab({super.key, required this.onRefresh});
  final VoidCallback onRefresh;

  @override
  State<AdminDashboardTab> createState() => _AdminDashboardTabState();
}

class _AdminDashboardTabState extends State<AdminDashboardTab> {
  late Future<List<AppTicket>> _future;

  @override
  void initState() {
    super.initState();
    _future = ApiClient.fetchTickets();
  }

  Future<void> _refresh() async {
    setState(() => _future = ApiClient.fetchTickets());
    await _future;
    widget.onRefresh();
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _refresh,
      child: FutureBuilder<List<AppTicket>>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return ListView(padding: const EdgeInsets.all(16), children: [const Center(child: CircularProgressIndicator())]);
          }
          if (snapshot.hasError) {
            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                const Text('Failed to load tickets.'),
                const SizedBox(height: 8),
                Text(snapshot.error.toString()),
              ],
            );
          }
          final tickets = snapshot.data ?? [];
          final openCount = tickets.where((t) => t.status == TicketStatus.open).length;
          final assignedCount = tickets.where((t) => t.status == TicketStatus.assigned).length;
          final inProgressCount = tickets.where((t) => t.status == TicketStatus.inProgress).length;
          final completedCount = tickets.where((t) => t.status == TicketStatus.completed).length;
          final total = tickets.isEmpty ? 1 : tickets.length;
          final openPct = openCount / total;
          final assignedPct = assignedCount / total;
          final inProgressPct = inProgressCount / total;
          final completedPct = completedCount / total;

          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              const Text('Overview', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
              const SizedBox(height: 10),
              GridView.count(
                shrinkWrap: true,
                crossAxisCount: 2,
                childAspectRatio: 1.45,
                crossAxisSpacing: 12,
                mainAxisSpacing: 12,
                physics: const NeverScrollableScrollPhysics(),
                children: [
                  MetricCard(title: 'Open', value: openCount.toString(), color: const Color(0xFFE67E22), icon: Icons.lock_open),
                  MetricCard(title: 'Assigned', value: assignedCount.toString(), color: const Color(0xFF247BA0), icon: Icons.person_add_alt_1),
                  MetricCard(title: 'In Progress', value: inProgressCount.toString(), color: const Color(0xFF118AB2), icon: Icons.autorenew),
                  MetricCard(title: 'Completed', value: completedCount.toString(), color: const Color(0xFF2A9D8F), icon: Icons.task_alt),
                ],
              ),
              const SizedBox(height: 14),
              _StatusChart(
                title: 'Ticket Status Distribution',
                rows: [
                  _ChartRow('Open', openCount, openPct, const Color(0xFFE67E22)),
                  _ChartRow('Assigned', assignedCount, assignedPct, const Color(0xFF247BA0)),
                  _ChartRow('In Progress', inProgressCount, inProgressPct, const Color(0xFF118AB2)),
                  _ChartRow('Completed', completedCount, completedPct, const Color(0xFF2A9D8F)),
                ],
              ),
              const SizedBox(height: 14),
              const Text('Recent Tickets', style: TextStyle(fontSize: 19, fontWeight: FontWeight.w700)),
              const SizedBox(height: 8),
              ...tickets.take(8).map((t) => TicketCard(ticket: t)),
            ],
          );
        },
      ),
    );
  }
}

class _StatusChart extends StatelessWidget {
  const _StatusChart({required this.title, required this.rows});
  final String title;
  final List<_ChartRow> rows;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: const Color(0xFFE0E8EE))),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
          const SizedBox(height: 12),
          ...rows.map((r) => _StatusBarRow(row: r)),
        ],
      ),
    );
  }
}

class _ChartRow {
  const _ChartRow(this.label, this.count, this.pct, this.color);
  final String label;
  final int count;
  final double pct;
  final Color color;
}

class _StatusBarRow extends StatelessWidget {
  const _StatusBarRow({required this.row});
  final _ChartRow row;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          SizedBox(width: 90, child: Text(row.label)),
          Expanded(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: LinearProgressIndicator(
                value: row.pct.clamp(0, 1),
                minHeight: 10,
                backgroundColor: row.color.withValues(alpha: 0.15),
                valueColor: AlwaysStoppedAnimation<Color>(row.color),
              ),
            ),
          ),
          const SizedBox(width: 10),
          SizedBox(width: 32, child: Text(row.count.toString())),
        ],
      ),
    );
  }
}

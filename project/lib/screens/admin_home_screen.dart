import 'package:flutter/material.dart';

import '../api/auth_store.dart';
import '../widgets/top_header.dart';
import 'login_screen.dart';
import 'tabs/admin_dashboard_tab.dart';
import 'tabs/admin_reports_tab.dart';
import 'tabs/master_data_tab.dart';
import 'tabs/ticket_management_tab.dart';

class AdminHomeScreen extends StatefulWidget {
  const AdminHomeScreen({super.key});
  @override
  State<AdminHomeScreen> createState() => _AdminHomeScreenState();
}

class _AdminHomeScreenState extends State<AdminHomeScreen> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    final tabs = [
      _AdminTab('Dashboard', Icons.dashboard_customize, AdminDashboardTab(onRefresh: () => setState(() {}))),
      _AdminTab('Tickets', Icons.confirmation_num_outlined, TicketManagementTab(onRefresh: () => setState(() {}))),
      _AdminTab('Engineers', Icons.engineering_outlined, MasterDataTab(onRefresh: () => setState(() {}))),
      _AdminTab('Reports', Icons.description_outlined, AdminReportsTab(onRefresh: () => setState(() {}))),
    ];

    final isWide = MediaQuery.of(context).size.width >= 1000;

    return Scaffold(
      body: SafeArea(
        child: isWide
            ? Row(
                children: [
                  NavigationRail(
                    selectedIndex: _index,
                    onDestinationSelected: (v) => setState(() => _index = v),
                    extended: true,
                    labelType: NavigationRailLabelType.none,
                    leading: Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Column(
                        children: const [
                          Icon(Icons.support_agent, size: 28),
                          SizedBox(height: 6),
                          Text('Admin', style: TextStyle(fontWeight: FontWeight.w700)),
                        ],
                      ),
                    ),
                    destinations: tabs
                        .map((t) => NavigationRailDestination(icon: Icon(t.icon), label: Text(t.label)))
                        .toList(),
                  ),
                  const VerticalDivider(width: 1),
                  Expanded(
                    child: Column(
                      children: [
                        TopHeader(
                          title: 'Admin Control Center',
                          subtitle: 'Manage tickets, assignments, and engineers',
                          onLogout: () {
                            AuthStore.clear();
                            Navigator.of(context).pushAndRemoveUntil(MaterialPageRoute(builder: (_) => const LoginScreen()), (r) => false);
                          },
                        ),
                        Expanded(child: tabs[_index].widget),
                      ],
                    ),
                  ),
                ],
              )
            : Column(
                children: [
                  TopHeader(
                    title: 'Admin Control Center',
                    subtitle: 'Manage tickets, assignments, and engineers',
                    onLogout: () {
                      AuthStore.clear();
                      Navigator.of(context).pushAndRemoveUntil(MaterialPageRoute(builder: (_) => const LoginScreen()), (r) => false);
                    },
                  ),
                  Expanded(child: tabs[_index].widget),
                ],
              ),
      ),
      bottomNavigationBar: isWide
          ? null
          : NavigationBar(
              selectedIndex: _index,
              onDestinationSelected: (v) => setState(() => _index = v),
              destinations: tabs.map((t) => NavigationDestination(icon: Icon(t.icon), label: t.label)).toList(),
            ),
    );
  }
}

class _AdminTab {
  const _AdminTab(this.label, this.icon, this.widget);
  final String label;
  final IconData icon;
  final Widget widget;
}

import 'package:flutter/material.dart';

import '../widgets/top_header.dart';
import 'engineer_profile_screen.dart';
import 'tabs/engineer_reports_tab.dart';
import 'tabs/engineer_tasks_tab.dart';

class EngineerHomeScreen extends StatefulWidget {
  const EngineerHomeScreen({super.key, required this.engineerName});
  final String engineerName;
  @override
  State<EngineerHomeScreen> createState() => _EngineerHomeScreenState();
}

class _EngineerHomeScreenState extends State<EngineerHomeScreen> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    final tabs = [
      EngineerTasksTab(engineerName: widget.engineerName, onRefresh: () => setState(() {})),
      EngineerReportsTab(engineerName: widget.engineerName),
      EngineerProfileScreen(engineerName: widget.engineerName),
    ];

    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            TopHeader(
              title: 'Engineer',
              subtitle: widget.engineerName,
            ),
            Expanded(child: tabs[_index]),
          ],
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (v) => setState(() => _index = v),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.assignment_outlined), label: 'My Tasks'),
          NavigationDestination(icon: Icon(Icons.description_outlined), label: 'Reports'),
          NavigationDestination(icon: Icon(Icons.settings_outlined), label: 'Profile'),
        ],
      ),
    );
  }
}


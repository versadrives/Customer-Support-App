import 'package:flutter/material.dart';

class TopHeader extends StatelessWidget {
  const TopHeader({super.key, required this.title, required this.subtitle, this.onLogout});

  final String title;
  final String subtitle;
  final VoidCallback? onLogout;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.fromLTRB(18, 16, 10, 16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        gradient: const LinearGradient(colors: [Color(0xFF0E61A5), Color(0xFF4C8FD0)], begin: Alignment.topLeft, end: Alignment.bottomRight),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.12),
            blurRadius: 26,
            offset: const Offset(0, 12),
          )
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 46,
            height: 46,
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(16),
            ),
            child: const Icon(Icons.engineering, color: Colors.white),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 20)),
                const SizedBox(height: 4),
                Text(subtitle, style: const TextStyle(color: Color(0xFFDDE9F5))),
              ],
            ),
          ),
          if (onLogout != null)
            IconButton(onPressed: onLogout, icon: const Icon(Icons.logout, color: Colors.white)),
        ],
      ),
    );
  }
}


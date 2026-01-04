import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/providers/auth_provider.dart';

/// Settings screen
class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authStateProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
      ),
      body: ListView(
        children: [
          // Profile section
          Card(
            margin: const EdgeInsets.all(16),
            child: ListTile(
              leading: CircleAvatar(
                radius: 25,
                backgroundColor: Theme.of(context).colorScheme.primaryContainer,
                child: Text(
                  authState.user?.name?.substring(0, 1).toUpperCase() ?? 'U',
                  style: const TextStyle(fontSize: 20),
                ),
              ),
              title: Text(authState.user?.name ?? 'User'),
              subtitle: Text(authState.user?.role.toUpperCase() ?? 'STAFF'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () {
                // TODO: Edit profile
              },
            ),
          ),

          // Clinic section
          _SettingsSection(
            title: 'Clinic',
            items: [
              _SettingsItem(
                icon: Icons.business,
                title: 'Clinic Profile',
                subtitle: 'Update clinic information',
                onTap: () {},
              ),
              _SettingsItem(
                icon: Icons.schedule,
                title: 'Working Hours',
                subtitle: 'Configure doctor schedules',
                onTap: () {},
              ),
              _SettingsItem(
                icon: Icons.medical_services,
                title: 'Services',
                subtitle: 'Manage services and pricing',
                onTap: () {},
              ),
            ],
          ),

          // Analytics & Reports section
          _SettingsSection(
            title: 'Analytics & Reports',
            items: [
              _SettingsItem(
                icon: Icons.analytics,
                title: 'Analytics Dashboard',
                subtitle: 'View appointment and revenue stats',
                onTap: () => context.goNamed('analytics'),
              ),
              _SettingsItem(
                icon: Icons.hourglass_empty,
                title: 'Waitlist Management',
                subtitle: 'Manage patient waiting queue',
                onTap: () => context.goNamed('waitlist'),
              ),
            ],
          ),

          // Notifications section
          _SettingsSection(
            title: 'Notifications',
            items: [
              _SettingsItem(
                icon: Icons.notifications,
                title: 'Push Notifications',
                trailing: Switch(
                  value: true,
                  onChanged: (value) {},
                ),
              ),
              _SettingsItem(
                icon: Icons.sms,
                title: 'SMS Reminders',
                trailing: Switch(
                  value: true,
                  onChanged: (value) {},
                ),
              ),
              _SettingsItem(
                icon: Icons.chat,
                title: 'WhatsApp Integration',
                subtitle: 'Send reminders via WhatsApp',
                onTap: () {},
              ),
            ],
          ),

          // Appearance section
          _SettingsSection(
            title: 'Appearance',
            items: [
              _SettingsItem(
                icon: Icons.dark_mode,
                title: 'Dark Mode',
                trailing: Switch(
                  value: false,
                  onChanged: (value) {},
                ),
              ),
              _SettingsItem(
                icon: Icons.language,
                title: 'Language',
                subtitle: 'English',
                onTap: () {},
              ),
            ],
          ),

          // Support section
          _SettingsSection(
            title: 'Support',
            items: [
              _SettingsItem(
                icon: Icons.help,
                title: 'Help Center',
                onTap: () {},
              ),
              _SettingsItem(
                icon: Icons.feedback,
                title: 'Send Feedback',
                onTap: () {},
              ),
              _SettingsItem(
                icon: Icons.info,
                title: 'About',
                subtitle: 'Version 0.1.0',
                onTap: () {},
              ),
            ],
          ),

          // Logout
          Padding(
            padding: const EdgeInsets.all(16),
            child: OutlinedButton.icon(
              onPressed: () async {
                final confirmed = await showDialog<bool>(
                  context: context,
                  builder: (context) => AlertDialog(
                    title: const Text('Logout'),
                    content: const Text('Are you sure you want to logout?'),
                    actions: [
                      TextButton(
                        onPressed: () => Navigator.pop(context, false),
                        child: const Text('Cancel'),
                      ),
                      TextButton(
                        onPressed: () => Navigator.pop(context, true),
                        child: const Text('Logout'),
                      ),
                    ],
                  ),
                );

                if (confirmed == true) {
                  await ref.read(authStateProvider.notifier).logout();
                  if (context.mounted) {
                    context.goNamed('login');
                  }
                }
              },
              icon: const Icon(Icons.logout, color: Colors.red),
              label: const Text(
                'Logout',
                style: TextStyle(color: Colors.red),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SettingsSection extends StatelessWidget {
  final String title;
  final List<_SettingsItem> items;

  const _SettingsSection({
    required this.title,
    required this.items,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
          child: Text(
            title,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  color: Colors.grey,
                  fontWeight: FontWeight.bold,
                ),
          ),
        ),
        ...items,
      ],
    );
  }
}

class _SettingsItem extends StatelessWidget {
  final IconData icon;
  final String title;
  final String? subtitle;
  final Widget? trailing;
  final VoidCallback? onTap;

  const _SettingsItem({
    required this.icon,
    required this.title,
    this.subtitle,
    this.trailing,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(icon),
      title: Text(title),
      subtitle: subtitle != null ? Text(subtitle!) : null,
      trailing: trailing ?? (onTap != null ? const Icon(Icons.chevron_right) : null),
      onTap: onTap,
    );
  }
}

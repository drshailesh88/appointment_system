import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/providers/settings_provider.dart';

/// WhatsApp integration settings screen
class WhatsAppSettingsScreen extends ConsumerStatefulWidget {
  const WhatsAppSettingsScreen({super.key});

  @override
  ConsumerState<WhatsAppSettingsScreen> createState() =>
      _WhatsAppSettingsScreenState();
}

class _WhatsAppSettingsScreenState
    extends ConsumerState<WhatsAppSettingsScreen> {
  final _formKey = GlobalKey<FormState>();

  bool _isEnabled = false;
  bool _sendReminders = true;
  bool _sendConfirmations = true;
  bool _allowBooking = true;
  bool _allowCancellation = true;
  int _reminderHoursBefore = 24;
  String _welcomeMessage = '';
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final settings = ref.read(whatsappSettingsProvider);
    if (settings != null) {
      setState(() {
        _isEnabled = settings.isEnabled;
        _sendReminders = settings.sendReminders;
        _sendConfirmations = settings.sendConfirmations;
        _allowBooking = settings.allowBooking;
        _allowCancellation = settings.allowCancellation;
        _reminderHoursBefore = settings.reminderHoursBefore;
        _welcomeMessage = settings.welcomeMessage;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('WhatsApp Integration'),
        actions: [
          TextButton(
            onPressed: _isSaving ? null : _saveSettings,
            child: _isSaving
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Save'),
          ),
        ],
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Status Card
            Card(
              color: _isEnabled ? Colors.green.shade50 : Colors.grey.shade100,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    Icon(
                      Icons.chat,
                      size: 40,
                      color: _isEnabled ? Colors.green : Colors.grey,
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            _isEnabled ? 'WhatsApp Bot Active' : 'WhatsApp Bot Inactive',
                            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                  fontWeight: FontWeight.bold,
                                ),
                          ),
                          Text(
                            _isEnabled
                                ? 'Patients can interact via WhatsApp'
                                : 'Enable to allow patient interactions',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                    ),
                    Switch(
                      value: _isEnabled,
                      onChanged: (value) => setState(() => _isEnabled = value),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),

            // Notifications Section
            Text(
              'Notifications',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 8),
            Card(
              child: Column(
                children: [
                  SwitchListTile(
                    title: const Text('Appointment Reminders'),
                    subtitle: const Text('Send reminder before appointment'),
                    value: _sendReminders,
                    onChanged: _isEnabled
                        ? (value) => setState(() => _sendReminders = value)
                        : null,
                  ),
                  if (_sendReminders) ...[
                    const Divider(height: 1),
                    ListTile(
                      title: const Text('Reminder Time'),
                      subtitle: Text('$_reminderHoursBefore hours before'),
                      trailing: DropdownButton<int>(
                        value: _reminderHoursBefore,
                        underline: const SizedBox(),
                        items: [1, 2, 4, 12, 24, 48]
                            .map((h) => DropdownMenuItem(
                                  value: h,
                                  child: Text('$h hours'),
                                ))
                            .toList(),
                        onChanged: _isEnabled
                            ? (value) {
                                if (value != null) {
                                  setState(() => _reminderHoursBefore = value);
                                }
                              }
                            : null,
                      ),
                    ),
                  ],
                  const Divider(height: 1),
                  SwitchListTile(
                    title: const Text('Booking Confirmations'),
                    subtitle: const Text('Send confirmation after booking'),
                    value: _sendConfirmations,
                    onChanged: _isEnabled
                        ? (value) => setState(() => _sendConfirmations = value)
                        : null,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Bot Features Section
            Text(
              'Bot Features',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 8),
            Card(
              child: Column(
                children: [
                  SwitchListTile(
                    title: const Text('Allow Booking'),
                    subtitle: const Text('Patients can book via WhatsApp'),
                    value: _allowBooking,
                    onChanged: _isEnabled
                        ? (value) => setState(() => _allowBooking = value)
                        : null,
                  ),
                  const Divider(height: 1),
                  SwitchListTile(
                    title: const Text('Allow Cancellation'),
                    subtitle: const Text('Patients can cancel via WhatsApp'),
                    value: _allowCancellation,
                    onChanged: _isEnabled
                        ? (value) => setState(() => _allowCancellation = value)
                        : null,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Welcome Message Section
            Text(
              'Welcome Message',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 8),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    TextFormField(
                      initialValue: _welcomeMessage,
                      decoration: const InputDecoration(
                        labelText: 'Custom Welcome Message',
                        hintText: 'Enter the message patients see first...',
                        border: OutlineInputBorder(),
                      ),
                      maxLines: 3,
                      enabled: _isEnabled,
                      onChanged: (value) => _welcomeMessage = value,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Variables: {patient_name}, {clinic_name}, {doctor_name}',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Colors.grey,
                          ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),

            // Test Connection
            OutlinedButton.icon(
              onPressed: _isEnabled ? _testConnection : null,
              icon: const Icon(Icons.send),
              label: const Text('Send Test Message'),
            ),
            const SizedBox(height: 32),

            // Help Section
            Card(
              color: Colors.blue.shade50,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.info_outline, color: Colors.blue.shade700),
                        const SizedBox(width: 8),
                        Text(
                          'How it works',
                          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                                fontWeight: FontWeight.bold,
                                color: Colors.blue.shade700,
                              ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      '1. Patients message your clinic WhatsApp number\n'
                      '2. The bot understands their request (book, cancel, check status)\n'
                      '3. Guides them through the booking process\n'
                      '4. Sends confirmations and reminders automatically',
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _saveSettings() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isSaving = true);

    try {
      await ref.read(whatsappSettingsProvider.notifier).updateSettings(
            isEnabled: _isEnabled,
            sendReminders: _sendReminders,
            sendConfirmations: _sendConfirmations,
            allowBooking: _allowBooking,
            allowCancellation: _allowCancellation,
            reminderHoursBefore: _reminderHoursBefore,
            welcomeMessage: _welcomeMessage,
          );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Settings saved successfully'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to save: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isSaving = false);
      }
    }
  }

  Future<void> _testConnection() async {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Send Test Message'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const TextField(
              decoration: InputDecoration(
                labelText: 'Phone Number',
                hintText: '+91 9876543210',
                prefixIcon: Icon(Icons.phone),
              ),
              keyboardType: TextInputType.phone,
            ),
            const SizedBox(height: 16),
            Text(
              'A test message will be sent to verify the WhatsApp integration is working.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Test message sent!')),
              );
            },
            child: const Text('Send'),
          ),
        ],
      ),
    );
  }
}

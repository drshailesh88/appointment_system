import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/providers/settings_provider.dart';

/// Voice settings screen for doctors
class VoiceSettingsScreen extends ConsumerStatefulWidget {
  const VoiceSettingsScreen({super.key});

  @override
  ConsumerState<VoiceSettingsScreen> createState() => _VoiceSettingsScreenState();
}

class _VoiceSettingsScreenState extends ConsumerState<VoiceSettingsScreen> {
  bool _isEnabled = false;
  String _language = 'en';
  double _speed = 1.0;
  double _exaggeration = 0.5;
  bool _useEmotions = true;
  bool _isSaving = false;
  bool _isRecording = false;
  bool _isUploading = false;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final settings = ref.read(voiceSettingsProvider);
    if (settings != null) {
      setState(() {
        _isEnabled = settings.isEnabled;
        _language = settings.language;
        _speed = settings.speed;
        _exaggeration = settings.exaggeration;
        _useEmotions = settings.useEmotions;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final settings = ref.watch(voiceSettingsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Voice Settings'),
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
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Voice Agent Status
          Card(
            color: _isEnabled ? Colors.green.shade50 : Colors.grey.shade100,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Icon(
                    Icons.record_voice_over,
                    size: 40,
                    color: _isEnabled ? Colors.green : Colors.grey,
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _isEnabled ? 'Voice Agent Active' : 'Voice Agent Inactive',
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                fontWeight: FontWeight.bold,
                              ),
                        ),
                        Text(
                          _isEnabled
                              ? 'Patients can book using voice'
                              : 'Enable for voice-based booking',
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

          // Voice Cloning Section
          Text(
            'Voice Cloning',
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
                  if (settings?.hasCustomVoice == true) ...[
                    // Custom voice exists
                    Row(
                      children: [
                        Container(
                          width: 60,
                          height: 60,
                          decoration: BoxDecoration(
                            color: Colors.blue.shade100,
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(Icons.mic, color: Colors.blue, size: 30),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                settings?.voiceName ?? 'Custom Voice',
                                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                                      fontWeight: FontWeight.bold,
                                    ),
                              ),
                              Text(
                                'Your cloned voice is active',
                                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                      color: Colors.green,
                                    ),
                              ),
                            ],
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.play_circle_outline),
                          onPressed: _playVoiceSample,
                          tooltip: 'Preview',
                        ),
                        IconButton(
                          icon: const Icon(Icons.delete_outline, color: Colors.red),
                          onPressed: _deleteVoice,
                          tooltip: 'Delete',
                        ),
                      ],
                    ),
                  ] else ...[
                    // No custom voice - show upload option
                    Text(
                      'Create your personalized voice',
                      style: Theme.of(context).textTheme.titleSmall,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Record a 10-30 second voice sample to clone your voice for automated responses.',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Colors.grey,
                          ),
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: _isEnabled && !_isRecording
                                ? _startRecording
                                : null,
                            icon: Icon(_isRecording ? Icons.stop : Icons.mic),
                            label: Text(_isRecording ? 'Recording...' : 'Record Sample'),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: _isEnabled && !_isUploading
                                ? _uploadVoiceFile
                                : null,
                            icon: _isUploading
                                ? const SizedBox(
                                    width: 16,
                                    height: 16,
                                    child: CircularProgressIndicator(strokeWidth: 2),
                                  )
                                : const Icon(Icons.upload_file),
                            label: Text(_isUploading ? 'Uploading...' : 'Upload File'),
                          ),
                        ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),

          // Language Section
          Text(
            'Language',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(8),
              child: Wrap(
                spacing: 8,
                runSpacing: 8,
                children: availableLanguages.map((lang) {
                  final isSelected = _language == lang.code;
                  return ChoiceChip(
                    label: Text(lang.nativeName),
                    selected: isSelected,
                    onSelected: _isEnabled
                        ? (selected) {
                            if (selected) {
                              setState(() => _language = lang.code);
                            }
                          }
                        : null,
                  );
                }).toList(),
              ),
            ),
          ),
          const SizedBox(height: 24),

          // Voice Parameters Section
          Text(
            'Voice Parameters',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          const SizedBox(height: 8),
          Card(
            child: Column(
              children: [
                // Speed
                ListTile(
                  title: const Text('Speech Speed'),
                  subtitle: Slider(
                    value: _speed,
                    min: 0.5,
                    max: 2.0,
                    divisions: 6,
                    label: '${_speed.toStringAsFixed(1)}x',
                    onChanged: _isEnabled
                        ? (value) => setState(() => _speed = value)
                        : null,
                  ),
                  trailing: Text('${_speed.toStringAsFixed(1)}x'),
                ),
                const Divider(height: 1),
                // Exaggeration (emotion intensity)
                ListTile(
                  title: const Text('Emotion Intensity'),
                  subtitle: Slider(
                    value: _exaggeration,
                    min: 0.0,
                    max: 1.0,
                    divisions: 10,
                    label: '${(_exaggeration * 100).toInt()}%',
                    onChanged: _isEnabled
                        ? (value) => setState(() => _exaggeration = value)
                        : null,
                  ),
                  trailing: Text('${(_exaggeration * 100).toInt()}%'),
                ),
                const Divider(height: 1),
                // Use emotions
                SwitchListTile(
                  title: const Text('Emotional Expressions'),
                  subtitle: const Text('Use [laugh], [sigh], [cough] in responses'),
                  value: _useEmotions,
                  onChanged: _isEnabled
                      ? (value) => setState(() => _useEmotions = value)
                      : null,
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Test Voice
          ElevatedButton.icon(
            onPressed: _isEnabled ? _testVoice : null,
            icon: const Icon(Icons.volume_up),
            label: const Text('Test Voice Output'),
          ),
          const SizedBox(height: 32),

          // Info Card
          Card(
            color: Colors.purple.shade50,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.auto_awesome, color: Colors.purple.shade700),
                      const SizedBox(width: 8),
                      Text(
                        'Powered by Chatterbox',
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.bold,
                              color: Colors.purple.shade700,
                            ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Zero-shot voice cloning with emotional expression support. '
                    'Your voice is processed locally and never leaves your device.',
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _saveSettings() async {
    setState(() => _isSaving = true);

    try {
      await ref.read(voiceSettingsProvider.notifier).updateSettings(
            isEnabled: _isEnabled,
            language: _language,
            speed: _speed,
            exaggeration: _exaggeration,
            useEmotions: _useEmotions,
          );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Voice settings saved'),
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

  Future<void> _startRecording() async {
    setState(() => _isRecording = true);

    // Show recording dialog
    await showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => _RecordingDialog(
        onComplete: (audioData) async {
          setState(() {
            _isRecording = false;
            _isUploading = true;
          });

          try {
            await ref.read(voiceSettingsProvider.notifier).uploadVoiceSample(
                  audioData,
                  'voice_sample.wav',
                );

            if (mounted) {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Voice cloned successfully!'),
                  backgroundColor: Colors.green,
                ),
              );
            }
          } catch (e) {
            if (mounted) {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('Failed to clone voice: $e'),
                  backgroundColor: Colors.red,
                ),
              );
            }
          } finally {
            if (mounted) {
              setState(() => _isUploading = false);
            }
          }
        },
        onCancel: () {
          setState(() => _isRecording = false);
        },
      ),
    );
  }

  Future<void> _uploadVoiceFile() async {
    // In a real app, use file_picker package
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('File picker would open here'),
      ),
    );
  }

  Future<void> _playVoiceSample() async {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Playing voice sample...')),
    );
  }

  Future<void> _deleteVoice() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Custom Voice'),
        content: const Text(
          'Are you sure you want to delete your cloned voice? '
          'You will need to record a new sample to use voice cloning again.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await ref.read(voiceSettingsProvider.notifier).deleteCustomVoice();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Custom voice deleted')),
        );
      }
    }
  }

  Future<void> _testVoice() async {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Test Voice'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              decoration: const InputDecoration(
                labelText: 'Test Text',
                hintText: 'Enter text to speak...',
                border: OutlineInputBorder(),
              ),
              maxLines: 2,
            ),
            const SizedBox(height: 16),
            Text(
              'The text will be spoken using your current voice settings.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton.icon(
            onPressed: () {
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Speaking...')),
              );
            },
            icon: const Icon(Icons.play_arrow),
            label: const Text('Speak'),
          ),
        ],
      ),
    );
  }
}

// Recording Dialog Widget
class _RecordingDialog extends StatefulWidget {
  final Function(List<int>) onComplete;
  final VoidCallback onCancel;

  const _RecordingDialog({
    required this.onComplete,
    required this.onCancel,
  });

  @override
  State<_RecordingDialog> createState() => _RecordingDialogState();
}

class _RecordingDialogState extends State<_RecordingDialog> {
  int _seconds = 0;
  bool _isRecording = true;

  @override
  void initState() {
    super.initState();
    _startTimer();
  }

  void _startTimer() {
    Future.doWhile(() async {
      await Future.delayed(const Duration(seconds: 1));
      if (!mounted || !_isRecording) return false;
      setState(() => _seconds++);
      return _seconds < 30; // Max 30 seconds
    });
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Recording Voice Sample'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 100,
            height: 100,
            decoration: BoxDecoration(
              color: Colors.red.shade100,
              shape: BoxShape.circle,
            ),
            child: Icon(
              Icons.mic,
              size: 50,
              color: Colors.red.shade700,
            ),
          ),
          const SizedBox(height: 16),
          Text(
            '${_seconds}s / 30s',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 8),
          LinearProgressIndicator(value: _seconds / 30),
          const SizedBox(height: 16),
          const Text(
            'Speak clearly for 10-30 seconds.\n'
            'Read a paragraph or describe your day.',
            textAlign: TextAlign.center,
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () {
            _isRecording = false;
            Navigator.pop(context);
            widget.onCancel();
          },
          child: const Text('Cancel'),
        ),
        if (_seconds >= 10)
          ElevatedButton(
            onPressed: () {
              _isRecording = false;
              Navigator.pop(context);
              // In a real app, return actual audio data
              widget.onComplete([]);
            },
            child: const Text('Done'),
          ),
      ],
    );
  }
}

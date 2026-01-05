import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/providers/telemedicine_provider.dart';
import 'consultation_screen.dart';

/// Waiting room screen for patients
class WaitingRoomScreen extends ConsumerStatefulWidget {
  final String consultationId;
  final String appointmentId;

  const WaitingRoomScreen({
    Key? key,
    required this.consultationId,
    required this.appointmentId,
  }) : super(key: key);

  @override
  ConsumerState<WaitingRoomScreen> createState() => _WaitingRoomScreenState();
}

class _WaitingRoomScreenState extends ConsumerState<WaitingRoomScreen> {
  @override
  void initState() {
    super.initState();
    _joinWaitingRoom();
  }

  Future<void> _joinWaitingRoom() async {
    final notifier = ref.read(telemedicineProvider.notifier);
    await notifier.joinWaitingRoom(
      widget.consultationId,
      deviceType: 'android', // or 'ios' based on Platform
      connectionType: 'wifi', // Could detect actual connection type
    );
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(telemedicineProvider);
    final waitingStatus = state.waitingRoomStatus;

    // If admitted to consultation, navigate to video call
    if (waitingStatus?.status == 'in_progress') {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _joinConsultation();
      });
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Waiting Room'),
        backgroundColor: Colors.blue[700],
      ),
      body: state.isLoading
          ? const Center(child: CircularProgressIndicator())
          : _buildWaitingContent(waitingStatus),
    );
  }

  Widget _buildWaitingContent(dynamic waitingStatus) {
    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Waiting animation
          _buildWaitingAnimation(),
          const SizedBox(height: 32),

          // Status message
          Text(
            'Please wait',
            style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          const SizedBox(height: 16),

          // Queue position
          if (waitingStatus != null) ...[
            _buildQueueInfo(waitingStatus),
            const SizedBox(height: 24),

            // Estimated wait time
            _buildWaitTimeInfo(waitingStatus),
          ],

          const SizedBox(height: 32),

          // Tips while waiting
          _buildTips(),

          const Spacer(),

          // Cancel button
          TextButton.icon(
            onPressed: () => _cancelConsultation(),
            icon: const Icon(Icons.close),
            label: const Text('Leave Waiting Room'),
            style: TextButton.styleFrom(
              foregroundColor: Colors.red,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildWaitingAnimation() {
    return Container(
      width: 120,
      height: 120,
      decoration: BoxDecoration(
        color: Colors.blue[50],
        shape: BoxShape.circle,
      ),
      child: Stack(
        alignment: Alignment.center,
        children: [
          const CircularProgressIndicator(
            strokeWidth: 3,
            valueColor: AlwaysStoppedAnimation<Color>(Colors.blue),
          ),
          Icon(
            Icons.video_call,
            size: 48,
            color: Colors.blue[700],
          ),
        ],
      ),
    );
  }

  Widget _buildQueueInfo(dynamic status) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.people, color: Colors.blue[700]),
            const SizedBox(width: 12),
            Text(
              status.waitingMessage,
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildWaitTimeInfo(dynamic status) {
    return Card(
      elevation: 2,
      color: Colors.orange[50],
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.access_time, color: Colors.orange[700]),
            const SizedBox(width: 12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Estimated wait time',
                  style: TextStyle(fontSize: 12),
                ),
                Text(
                  status.estimatedWaitMessage,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTips() {
    return Card(
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.lightbulb_outline, color: Colors.amber[700]),
                const SizedBox(width: 8),
                const Text(
                  'Tips while you wait',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            _buildTipItem('Keep your device charged'),
            _buildTipItem('Ensure you have a stable internet connection'),
            _buildTipItem('Find a quiet, well-lit place for the call'),
            _buildTipItem('Have your medical reports ready if needed'),
          ],
        ),
      ),
    );
  }

  Widget _buildTipItem(String tip) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          const Icon(Icons.check_circle, size: 16, color: Colors.green),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              tip,
              style: const TextStyle(fontSize: 14),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _joinConsultation() async {
    final notifier = ref.read(telemedicineProvider.notifier);
    final joinResponse = await notifier.joinConsultation(widget.consultationId);

    if (joinResponse != null && mounted) {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (context) => ConsultationScreen(
            consultationId: widget.consultationId,
            roomUrl: joinResponse.roomUrl,
            jwtToken: joinResponse.jwtToken,
            roomName: joinResponse.roomName,
          ),
        ),
      );
    }
  }

  Future<void> _cancelConsultation() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Leave Waiting Room?'),
        content: const Text(
            'Are you sure you want to leave the waiting room? You will lose your place in the queue.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('No, Stay'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Yes, Leave'),
          ),
        ],
      ),
    );

    if (confirm == true && mounted) {
      Navigator.pop(context);
    }
  }
}

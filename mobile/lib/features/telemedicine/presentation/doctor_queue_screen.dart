import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/providers/telemedicine_provider.dart';
import 'consultation_screen.dart';

/// Doctor's waiting queue screen
class DoctorQueueScreen extends ConsumerStatefulWidget {
  const DoctorQueueScreen({Key? key}) : super(key: key);

  @override
  ConsumerState<DoctorQueueScreen> createState() => _DoctorQueueScreenState();
}

class _DoctorQueueScreenState extends ConsumerState<DoctorQueueScreen> {
  @override
  void initState() {
    super.initState();
    _loadQueue();
    // Start polling for queue updates
    ref.read(telemedicineProvider.notifier).startDoctorQueuePolling();
  }

  @override
  void dispose() {
    // Stop polling when screen is closed
    ref.read(telemedicineProvider.notifier).stopDoctorQueuePolling();
    super.dispose();
  }

  Future<void> _loadQueue() async {
    await ref.read(telemedicineProvider.notifier).getDoctorQueue();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(telemedicineProvider);
    final queue = state.doctorQueue;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Waiting Patients'),
        backgroundColor: Colors.blue[700],
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadQueue,
          ),
        ],
      ),
      body: state.isLoading && queue == null
          ? const Center(child: CircularProgressIndicator())
          : queue == null || queue.queue.isEmpty
              ? _buildEmptyState()
              : _buildQueueList(queue.queue),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.inbox_outlined,
            size: 80,
            color: Colors.grey[400],
          ),
          const SizedBox(height: 16),
          Text(
            'No patients waiting',
            style: TextStyle(
              fontSize: 18,
              color: Colors.grey[600],
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Patients will appear here when they\njoin the waiting room',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 14,
              color: Colors.grey[500],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildQueueList(List queue) {
    return Column(
      children: [
        // Queue header
        Container(
          padding: const EdgeInsets.all(16),
          color: Colors.blue[50],
          child: Row(
            children: [
              Icon(Icons.people, color: Colors.blue[700]),
              const SizedBox(width: 12),
              Text(
                '${queue.length} patient${queue.length != 1 ? 's' : ''} waiting',
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ),

        // Queue list
        Expanded(
          child: RefreshIndicator(
            onRefresh: _loadQueue,
            child: ListView.builder(
              itemCount: queue.length,
              itemBuilder: (context, index) {
                final patient = queue[index];
                return _buildPatientCard(patient, index);
              },
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildPatientCard(dynamic patient, int index) {
    final waitTime = patient.waitTimeMinutes;

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      elevation: patient.isEmergency ? 4 : 2,
      color: patient.isEmergency ? Colors.red[50] : null,
      child: InkWell(
        onTap: () => _admitPatient(patient),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Patient info and emergency badge
              Row(
                children: [
                  // Position badge
                  Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      color: patient.isEmergency
                          ? Colors.red
                          : Colors.blue[700],
                      shape: BoxShape.circle,
                    ),
                    child: Center(
                      child: Text(
                        '${index + 1}',
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),

                  // Patient name
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          patient.patientName,
                          style: const TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        if (patient.isEmergency)
                          Container(
                            margin: const EdgeInsets.only(top: 4),
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 2,
                            ),
                            decoration: BoxDecoration(
                              color: Colors.red,
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: const Text(
                              'EMERGENCY',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),

                  // Wait time
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Icon(
                        Icons.access_time,
                        size: 16,
                        color: _getWaitTimeColor(waitTime),
                      ),
                      Text(
                        _formatWaitTime(waitTime),
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: _getWaitTimeColor(waitTime),
                        ),
                      ),
                    ],
                  ),
                ],
              ),

              // Chief complaint
              if (patient.chiefComplaint != null) ...[
                const SizedBox(height: 12),
                Row(
                  children: [
                    Icon(Icons.medical_services_outlined,
                        size: 16, color: Colors.grey[600]),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        patient.chiefComplaint,
                        style: TextStyle(
                          fontSize: 14,
                          color: Colors.grey[700],
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ],

              const SizedBox(height: 12),

              // Action button
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: () => _admitPatient(patient),
                  icon: const Icon(Icons.video_call),
                  label: const Text('Admit Patient'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor:
                        patient.isEmergency ? Colors.red : Colors.blue[700],
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Color _getWaitTimeColor(int minutes) {
    if (minutes > 30) return Colors.red;
    if (minutes > 15) return Colors.orange;
    return Colors.green;
  }

  String _formatWaitTime(int minutes) {
    if (minutes >= 60) {
      final hours = minutes ~/ 60;
      final mins = minutes % 60;
      return '${hours}h ${mins}m';
    }
    return '${minutes}m';
  }

  Future<void> _admitPatient(dynamic patient) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Admit Patient?'),
        content: Text(
            'Start video consultation with ${patient.patientName}?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Start Consultation'),
          ),
        ],
      ),
    );

    if (confirm != true || !mounted) return;

    // Admit patient
    final notifier = ref.read(telemedicineProvider.notifier);
    final joinResponse = await notifier.admitPatient(patient.consultationId);

    if (joinResponse != null && mounted) {
      // Navigate to video call
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (context) => ConsultationScreen(
            consultationId: patient.consultationId,
            roomUrl: joinResponse.roomUrl,
            jwtToken: joinResponse.jwtToken,
            roomName: joinResponse.roomName,
          ),
        ),
      );
    } else if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Failed to admit patient'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }
}

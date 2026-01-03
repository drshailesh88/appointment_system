import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../../core/models/doctor.dart';
import '../../../core/models/patient.dart';
import '../../../core/providers/appointments_provider.dart';
import '../../../core/providers/doctors_provider.dart';
import '../../../core/providers/patients_provider.dart';

/// Book appointment screen
class BookAppointmentScreen extends ConsumerStatefulWidget {
  const BookAppointmentScreen({super.key});

  @override
  ConsumerState<BookAppointmentScreen> createState() =>
      _BookAppointmentScreenState();
}

class _BookAppointmentScreenState extends ConsumerState<BookAppointmentScreen> {
  int _currentStep = 0;
  Doctor? _selectedDoctor;
  DateTime? _selectedDate;
  Map<String, dynamic>? _selectedSlot;
  Patient? _selectedPatient;
  String _appointmentType = 'new_consultation';
  final _complaintController = TextEditingController();
  final _patientSearchController = TextEditingController();
  bool _isBooking = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(doctorsProvider.notifier).loadDoctors();
    });
  }

  @override
  void dispose() {
    _complaintController.dispose();
    _patientSearchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final doctorsState = ref.watch(doctorsProvider);
    final patientsState = ref.watch(patientsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Book Appointment'),
      ),
      body: Stepper(
        currentStep: _currentStep,
        onStepContinue: _canContinue() ? _handleContinue : null,
        onStepCancel: _currentStep > 0
            ? () => setState(() => _currentStep--)
            : null,
        controlsBuilder: (context, details) {
          return Padding(
            padding: const EdgeInsets.only(top: 16),
            child: Row(
              children: [
                if (_currentStep < 3)
                  ElevatedButton(
                    onPressed: _canContinue() ? details.onStepContinue : null,
                    child: const Text('Continue'),
                  )
                else
                  ElevatedButton(
                    onPressed: _isBooking ? null : _bookAppointment,
                    child: _isBooking
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text('Book Appointment'),
                  ),
                if (_currentStep > 0) ...[
                  const SizedBox(width: 8),
                  TextButton(
                    onPressed: details.onStepCancel,
                    child: const Text('Back'),
                  ),
                ],
              ],
            ),
          );
        },
        steps: [
          // Step 1: Select Doctor
          Step(
            title: const Text('Select Doctor'),
            isActive: _currentStep >= 0,
            state: _currentStep > 0 ? StepState.complete : StepState.indexed,
            content: _buildDoctorSelection(doctorsState),
          ),

          // Step 2: Select Date & Time
          Step(
            title: const Text('Select Date & Time'),
            isActive: _currentStep >= 1,
            state: _currentStep > 1 ? StepState.complete : StepState.indexed,
            content: _buildDateTimeSelection(),
          ),

          // Step 3: Select Patient
          Step(
            title: const Text('Select Patient'),
            isActive: _currentStep >= 2,
            state: _currentStep > 2 ? StepState.complete : StepState.indexed,
            content: _buildPatientSelection(patientsState),
          ),

          // Step 4: Appointment Details
          Step(
            title: const Text('Appointment Details'),
            isActive: _currentStep >= 3,
            state: StepState.indexed,
            content: _buildAppointmentDetails(),
          ),
        ],
      ),
    );
  }

  bool _canContinue() {
    switch (_currentStep) {
      case 0:
        return _selectedDoctor != null;
      case 1:
        return _selectedDate != null && _selectedSlot != null;
      case 2:
        return _selectedPatient != null;
      case 3:
        return true;
      default:
        return false;
    }
  }

  void _handleContinue() {
    if (_currentStep < 3) {
      setState(() => _currentStep++);

      // Load slots when moving to date/time selection
      if (_currentStep == 1 && _selectedDoctor != null) {
        final today = DateFormat('yyyy-MM-dd').format(DateTime.now());
        ref.read(doctorsProvider.notifier).loadAvailableSlots(
              _selectedDoctor!.id,
              today,
              durationMinutes: _selectedDoctor!.slotDuration,
            );
      }
    }
  }

  Widget _buildDoctorSelection(DoctorsState state) {
    if (state.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (state.error != null) {
      return Center(
        child: Column(
          children: [
            Text('Error: ${state.error}'),
            ElevatedButton(
              onPressed: () => ref.read(doctorsProvider.notifier).loadDoctors(),
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (state.doctors.isEmpty) {
      return const Center(child: Text('No doctors available'));
    }

    return Column(
      children: state.doctors.map((doctor) {
        return RadioListTile<Doctor>(
          value: doctor,
          groupValue: _selectedDoctor,
          onChanged: (value) {
            setState(() => _selectedDoctor = value);
          },
          title: Text(doctor.name),
          subtitle: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (doctor.specialization != null)
                Text(doctor.specialization!),
              Text(
                '${doctor.feeDisplay} • ${doctor.slotDuration} min slots',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
          secondary: CircleAvatar(
            backgroundColor: Theme.of(context).colorScheme.primaryContainer,
            child: Text(doctor.name.substring(0, 1)),
          ),
        );
      }).toList(),
    );
  }

  Widget _buildDateTimeSelection() {
    final doctorsState = ref.watch(doctorsProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Date selection
        Text(
          'Select Date',
          style: Theme.of(context).textTheme.titleSmall,
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          children: List.generate(7, (index) {
            final date = DateTime.now().add(Duration(days: index));
            final isSelected = _selectedDate?.day == date.day &&
                _selectedDate?.month == date.month;
            return ChoiceChip(
              label: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(DateFormat('EEE').format(date)),
                  Text(DateFormat('d MMM').format(date)),
                ],
              ),
              selected: isSelected,
              onSelected: (selected) {
                setState(() {
                  _selectedDate = date;
                  _selectedSlot = null;
                });
                // Load slots for selected date
                if (_selectedDoctor != null) {
                  final dateStr = DateFormat('yyyy-MM-dd').format(date);
                  ref.read(doctorsProvider.notifier).loadAvailableSlots(
                        _selectedDoctor!.id,
                        dateStr,
                        durationMinutes: _selectedDoctor!.slotDuration,
                      );
                }
              },
            );
          }),
        ),
        const SizedBox(height: 16),

        // Time slot selection
        Text(
          'Select Time',
          style: Theme.of(context).textTheme.titleSmall,
        ),
        const SizedBox(height: 8),

        if (doctorsState.isLoading)
          const Center(child: CircularProgressIndicator())
        else if (doctorsState.availableSlots.isEmpty)
          const Card(
            child: Padding(
              padding: EdgeInsets.all(16),
              child: Text('No slots available. Select a date to view slots.'),
            ),
          )
        else
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: doctorsState.availableSlots.map((slot) {
              final startTime = slot['start_time'] as String? ?? '';
              final isAvailable = slot['available'] as bool? ?? true;
              final isSelected = _selectedSlot == slot;

              return ChoiceChip(
                label: Text(_formatTimeSlot(startTime)),
                selected: isSelected,
                onSelected: isAvailable
                    ? (selected) {
                        setState(() => _selectedSlot = slot);
                      }
                    : null,
                backgroundColor: isAvailable ? null : Colors.grey.shade300,
              );
            }).toList(),
          ),
      ],
    );
  }

  String _formatTimeSlot(String isoTime) {
    try {
      final dateTime = DateTime.parse(isoTime);
      return DateFormat('h:mm a').format(dateTime);
    } catch (e) {
      return isoTime;
    }
  }

  Widget _buildPatientSelection(PatientsState state) {
    return Column(
      children: [
        TextField(
          controller: _patientSearchController,
          decoration: const InputDecoration(
            hintText: 'Search patient by name or phone',
            prefixIcon: Icon(Icons.search),
          ),
          onChanged: (value) {
            if (value.length >= 2) {
              ref.read(patientsProvider.notifier).searchPatients(value);
            }
          },
        ),
        const SizedBox(height: 16),

        if (state.isSearching)
          const Center(child: CircularProgressIndicator())
        else if (state.searchResults.isEmpty && _patientSearchController.text.length >= 2)
          const Card(
            child: Padding(
              padding: EdgeInsets.all(16),
              child: Text('No patients found'),
            ),
          )
        else
          ...state.searchResults.map(
            (patient) => RadioListTile<Patient>(
              value: patient,
              groupValue: _selectedPatient,
              onChanged: (value) {
                setState(() => _selectedPatient = value);
              },
              title: Text(patient.name),
              subtitle: Text(patient.phone ?? patient.email ?? ''),
              secondary: CircleAvatar(
                backgroundColor: Theme.of(context).colorScheme.primaryContainer,
                child: Text(patient.name.substring(0, 1)),
              ),
            ),
          ),

        const SizedBox(height: 16),
        OutlinedButton.icon(
          onPressed: _showNewPatientDialog,
          icon: const Icon(Icons.person_add),
          label: const Text('Add New Patient'),
        ),
      ],
    );
  }

  Widget _buildAppointmentDetails() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextField(
          controller: _complaintController,
          maxLines: 3,
          decoration: const InputDecoration(
            labelText: 'Chief Complaint',
            hintText: 'Enter reason for visit...',
          ),
        ),
        const SizedBox(height: 16),
        DropdownButtonFormField<String>(
          decoration: const InputDecoration(
            labelText: 'Appointment Type',
          ),
          value: _appointmentType,
          items: const [
            DropdownMenuItem(
              value: 'new_consultation',
              child: Text('New Consultation'),
            ),
            DropdownMenuItem(
              value: 'follow_up',
              child: Text('Follow Up'),
            ),
            DropdownMenuItem(
              value: 'procedure',
              child: Text('Procedure'),
            ),
          ],
          onChanged: (value) {
            setState(() => _appointmentType = value ?? 'new_consultation');
          },
        ),
        const SizedBox(height: 24),

        // Summary
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Summary',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                const SizedBox(height: 12),
                _SummaryRow('Doctor', _selectedDoctor?.name ?? '-'),
                _SummaryRow(
                  'Date',
                  _selectedDate != null
                      ? DateFormat('EEEE, d MMMM yyyy').format(_selectedDate!)
                      : '-',
                ),
                _SummaryRow(
                  'Time',
                  _selectedSlot != null
                      ? _formatTimeSlot(_selectedSlot!['start_time'] ?? '')
                      : '-',
                ),
                _SummaryRow('Patient', _selectedPatient?.name ?? '-'),
                _SummaryRow(
                  'Fee',
                  _selectedDoctor?.feeDisplay ?? '-',
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  void _showNewPatientDialog() {
    final nameController = TextEditingController();
    final phoneController = TextEditingController();
    final emailController = TextEditingController();

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Add New Patient'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameController,
                decoration: const InputDecoration(labelText: 'Full Name *'),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: phoneController,
                decoration: const InputDecoration(labelText: 'Phone *'),
                keyboardType: TextInputType.phone,
              ),
              const SizedBox(height: 8),
              TextField(
                controller: emailController,
                decoration: const InputDecoration(labelText: 'Email'),
                keyboardType: TextInputType.emailAddress,
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              if (nameController.text.isNotEmpty &&
                  phoneController.text.isNotEmpty) {
                final patient = await ref
                    .read(patientsProvider.notifier)
                    .createPatient({
                  'name': nameController.text,
                  'phone': phoneController.text,
                  'email': emailController.text.isEmpty
                      ? null
                      : emailController.text,
                });

                if (patient != null && mounted) {
                  setState(() => _selectedPatient = patient);
                  Navigator.pop(context);
                }
              }
            },
            child: const Text('Add'),
          ),
        ],
      ),
    );
  }

  Future<void> _bookAppointment() async {
    if (_selectedDoctor == null ||
        _selectedDate == null ||
        _selectedSlot == null ||
        _selectedPatient == null) {
      return;
    }

    setState(() => _isBooking = true);

    try {
      final appointment =
          await ref.read(appointmentsProvider.notifier).createAppointment({
        'doctor_id': _selectedDoctor!.id,
        'patient_id': _selectedPatient!.id,
        'start_time': _selectedSlot!['start_time'],
        'end_time': _selectedSlot!['end_time'],
        'appointment_type': _appointmentType,
        'chief_complaint': _complaintController.text.isEmpty
            ? null
            : _complaintController.text,
      });

      if (mounted) {
        if (appointment != null) {
          showDialog(
            context: context,
            builder: (context) => AlertDialog(
              title: const Text('Appointment Booked!'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'The appointment has been successfully booked.',
                  ),
                  const SizedBox(height: 16),
                  Text('Patient: ${_selectedPatient!.name}'),
                  Text('Doctor: ${_selectedDoctor!.name}'),
                  Text(
                    'Date: ${DateFormat('d MMM yyyy').format(_selectedDate!)}',
                  ),
                  Text(
                    'Time: ${_formatTimeSlot(_selectedSlot!['start_time'] ?? '')}',
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'A confirmation will be sent to the patient.',
                    style: TextStyle(color: Colors.grey),
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () {
                    Navigator.pop(context);
                    context.goNamed('appointments');
                  },
                  child: const Text('OK'),
                ),
              ],
            ),
          );
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Failed to book appointment'),
              backgroundColor: Colors.red,
            ),
          );
        }
      }
    } finally {
      if (mounted) {
        setState(() => _isBooking = false);
      }
    }
  }
}

class _SummaryRow extends StatelessWidget {
  final String label;
  final String value;

  const _SummaryRow(this.label, this.value);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Colors.grey)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }
}

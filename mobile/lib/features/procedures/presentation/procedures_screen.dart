import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../core/models/procedure.dart';
import '../../../core/providers/procedures_provider.dart';
import '../../../core/providers/auth_provider.dart';
import '../../../core/providers/doctors_provider.dart';
import '../../../core/providers/patients_provider.dart';

/// Procedures Screen for logging and viewing medical procedures
///
/// Phase 9: Procedure & Intervention Tracking
class ProceduresScreen extends ConsumerStatefulWidget {
  const ProceduresScreen({super.key});

  @override
  ConsumerState<ProceduresScreen> createState() => _ProceduresScreenState();
}

class _ProceduresScreenState extends ConsumerState<ProceduresScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  String _selectedCategory = 'All';
  DateTime _startDate = DateTime.now().subtract(const Duration(days: 30));
  DateTime _endDate = DateTime.now();

  final List<String> _categories = [
    'All',
    'Cardiology',
    'Orthopedics',
    'Ophthalmology',
    'Dermatology',
    'Gastroenterology',
    'General',
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _loadData();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  void _loadData() {
    final authState = ref.read(authProvider);
    final clinicId = authState.user?.clinicId;
    if (clinicId != null) {
      final notifier = ref.read(proceduresProvider(clinicId).notifier);
      notifier.loadProcedures();
      notifier.loadStats();
      notifier.loadTypeCounts();
      notifier.loadTemplates();
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final clinicId = authState.user?.clinicId ?? '';
    final proceduresState = ref.watch(proceduresProvider(clinicId));

    return Scaffold(
      appBar: AppBar(
        title: const Text('Procedures'),
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(text: 'Log', icon: Icon(Icons.add_circle_outline)),
            Tab(text: 'Analytics', icon: Icon(Icons.analytics)),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.filter_list),
            onPressed: () => _showFilterDialog(clinicId),
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadData,
          ),
        ],
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildLogTab(clinicId, proceduresState),
          _buildAnalyticsTab(clinicId, proceduresState),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _showQuickLogDialog(clinicId),
        icon: const Icon(Icons.add),
        label: const Text('Quick Log'),
      ),
    );
  }

  Widget _buildLogTab(String clinicId, ProceduresState state) {
    if (state.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (state.error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 48, color: Colors.red),
            const SizedBox(height: 16),
            Text(state.error!, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _loadData,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (state.procedures.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.medical_services_outlined,
                size: 64, color: Colors.grey[400]),
            const SizedBox(height: 16),
            Text(
              'No procedures logged yet',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            const Text('Tap "Quick Log" to record a procedure'),
          ],
        ),
      );
    }

    return Column(
      children: [
        // Category filter chips
        SizedBox(
          height: 50,
          child: ListView.builder(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
            itemCount: _categories.length,
            itemBuilder: (context, index) {
              final category = _categories[index];
              return Padding(
                padding: const EdgeInsets.only(right: 8),
                child: ChoiceChip(
                  label: Text(category),
                  selected: _selectedCategory == category,
                  onSelected: (_) {
                    setState(() => _selectedCategory = category);
                    ref.read(proceduresProvider(clinicId).notifier)
                        .setCategory(category);
                  },
                ),
              );
            },
          ),
        ),
        // Procedures list
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(8),
            itemCount: state.procedures.length,
            itemBuilder: (context, index) {
              return _buildProcedureCard(state.procedures[index], clinicId);
            },
          ),
        ),
      ],
    );
  }

  Widget _buildProcedureCard(Procedure procedure, String clinicId) {
    final dateStr = DateFormat('MMM d, y').format(procedure.procedureDate);
    final outcomeColor = _getOutcomeColor(procedure.outcome);

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        onTap: () => _showProcedureDetails(procedure, clinicId),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: _getCategoryColor(procedure.category)
                          .withOpacity(0.1),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      procedure.category,
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: _getCategoryColor(procedure.category),
                      ),
                    ),
                  ),
                  const Spacer(),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: outcomeColor.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      procedure.outcome.toUpperCase(),
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                        color: outcomeColor,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                procedure.procedureType,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              if (procedure.subType != null) ...[
                const SizedBox(height: 2),
                Text(
                  procedure.subType!,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
              const SizedBox(height: 8),
              Row(
                children: [
                  const Icon(Icons.person, size: 16, color: Colors.grey),
                  const SizedBox(width: 4),
                  Expanded(
                    child: Text(
                      procedure.patientName ?? 'Unknown patient',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ),
                  const Icon(Icons.calendar_today, size: 14, color: Colors.grey),
                  const SizedBox(width: 4),
                  Text(
                    dateStr,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
              if (procedure.billedAmount != null) ...[
                const SizedBox(height: 4),
                Row(
                  children: [
                    const Icon(Icons.currency_rupee, size: 16, color: Colors.green),
                    Text(
                      NumberFormat('#,##0').format(procedure.billedAmount),
                      style: const TextStyle(
                        color: Colors.green,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildAnalyticsTab(String clinicId, ProceduresState state) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Stats overview
          if (state.stats != null) _buildStatsCards(state.stats!),
          const SizedBox(height: 24),

          // Procedure type breakdown
          Text(
            'Procedures by Type',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          const SizedBox(height: 12),
          if (state.typeCounts.isEmpty)
            const Card(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Center(
                  child: Text('No procedure data for this period'),
                ),
              ),
            )
          else
            ...state.typeCounts.map((tc) => _buildTypeCountCard(tc)),
        ],
      ),
    );
  }

  Widget _buildStatsCards(ProcedureStats stats) {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: _buildStatCard(
                'Total Procedures',
                stats.totalProcedures.toString(),
                Icons.medical_services,
                Colors.blue,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildStatCard(
                'Success Rate',
                '${stats.successRate.toStringAsFixed(1)}%',
                Icons.check_circle,
                Colors.green,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: _buildStatCard(
                'Total Billed',
                '₹${NumberFormat.compact().format(stats.totalBilled)}',
                Icons.currency_rupee,
                Colors.orange,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildStatCard(
                'Successful',
                stats.successfulCount.toString(),
                Icons.thumb_up,
                Colors.teal,
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildStatCard(
    String label,
    String value,
    IconData icon,
    Color color,
  ) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: color, size: 24),
            const SizedBox(height: 8),
            Text(
              value,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: color,
                  ),
            ),
            Text(
              label,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTypeCountCard(ProcedureTypeCount tc) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: _getCategoryColor(tc.category).withOpacity(0.1),
          child: Text(
            tc.count.toString(),
            style: TextStyle(
              fontWeight: FontWeight.bold,
              color: _getCategoryColor(tc.category),
            ),
          ),
        ),
        title: Text(tc.procedureType),
        subtitle: Text(tc.category),
        trailing: Text(
          '₹${NumberFormat.compact().format(tc.totalBilled)}',
          style: const TextStyle(
            fontWeight: FontWeight.bold,
            color: Colors.green,
          ),
        ),
      ),
    );
  }

  Color _getCategoryColor(String category) {
    switch (category.toLowerCase()) {
      case 'cardiology':
        return Colors.red;
      case 'orthopedics':
        return Colors.blue;
      case 'ophthalmology':
        return Colors.purple;
      case 'dermatology':
        return Colors.orange;
      case 'gastroenterology':
        return Colors.brown;
      default:
        return Colors.teal;
    }
  }

  Color _getOutcomeColor(String outcome) {
    switch (outcome.toLowerCase()) {
      case 'successful':
        return Colors.green;
      case 'partial':
        return Colors.orange;
      case 'failed':
        return Colors.red;
      case 'referred':
        return Colors.blue;
      default:
        return Colors.grey;
    }
  }

  void _showFilterDialog(String clinicId) {
    showModalBottomSheet(
      context: context,
      builder: (context) => Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Filter Procedures',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            Text('Date Range',
                style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () async {
                      final picked = await showDatePicker(
                        context: context,
                        initialDate: _startDate,
                        firstDate: DateTime(2020),
                        lastDate: DateTime.now(),
                      );
                      if (picked != null) {
                        setState(() => _startDate = picked);
                      }
                    },
                    icon: const Icon(Icons.calendar_today, size: 16),
                    label: Text(DateFormat('MMM d').format(_startDate)),
                  ),
                ),
                const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 8),
                  child: Text('to'),
                ),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () async {
                      final picked = await showDatePicker(
                        context: context,
                        initialDate: _endDate,
                        firstDate: DateTime(2020),
                        lastDate: DateTime.now(),
                      );
                      if (picked != null) {
                        setState(() => _endDate = picked);
                      }
                    },
                    icon: const Icon(Icons.calendar_today, size: 16),
                    label: Text(DateFormat('MMM d').format(_endDate)),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () {
                  Navigator.pop(context);
                  ref.read(proceduresProvider(clinicId).notifier).loadProcedures(
                        startDate: _startDate,
                        endDate: _endDate,
                        category: _selectedCategory == 'All'
                            ? null
                            : _selectedCategory,
                      );
                  ref.read(proceduresProvider(clinicId).notifier).loadStats(
                        startDate: _startDate,
                        endDate: _endDate,
                      );
                  ref.read(proceduresProvider(clinicId).notifier).loadTypeCounts(
                        startDate: _startDate,
                        endDate: _endDate,
                      );
                },
                child: const Text('Apply Filter'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _showQuickLogDialog(String clinicId) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(context).viewInsets.bottom,
        ),
        child: _QuickLogForm(
          clinicId: clinicId,
          onSubmit: () {
            Navigator.pop(context);
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('Procedure logged successfully!'),
                backgroundColor: Colors.green,
              ),
            );
          },
        ),
      ),
    );
  }

  void _showProcedureDetails(Procedure procedure, String clinicId) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => DraggableScrollableSheet(
        initialChildSize: 0.6,
        maxChildSize: 0.9,
        minChildSize: 0.4,
        expand: false,
        builder: (context, scrollController) => SingleChildScrollView(
          controller: scrollController,
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: Colors.grey[300],
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 6,
                    ),
                    decoration: BoxDecoration(
                      color: _getCategoryColor(procedure.category)
                          .withOpacity(0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      procedure.category,
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: _getCategoryColor(procedure.category),
                      ),
                    ),
                  ),
                  const Spacer(),
                  IconButton(
                    icon: const Icon(Icons.edit, color: Colors.blue),
                    onPressed: () {
                      Navigator.pop(context);
                      // TODO: Open edit dialog
                    },
                  ),
                  IconButton(
                    icon: const Icon(Icons.delete, color: Colors.red),
                    onPressed: () async {
                      final confirm = await showDialog<bool>(
                        context: context,
                        builder: (context) => AlertDialog(
                          title: const Text('Delete Procedure?'),
                          content: const Text(
                            'This action cannot be undone.',
                          ),
                          actions: [
                            TextButton(
                              onPressed: () => Navigator.pop(context, false),
                              child: const Text('Cancel'),
                            ),
                            ElevatedButton(
                              onPressed: () => Navigator.pop(context, true),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.red,
                              ),
                              child: const Text('Delete'),
                            ),
                          ],
                        ),
                      );
                      if (confirm == true) {
                        ref.read(proceduresProvider(clinicId).notifier)
                            .deleteProcedure(procedure.id);
                        Navigator.pop(context);
                      }
                    },
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Text(
                procedure.procedureType,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              if (procedure.subType != null)
                Text(
                  procedure.subType!,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: Colors.grey,
                      ),
                ),
              const SizedBox(height: 16),
              _buildDetailRow('Patient', procedure.patientName ?? 'Unknown'),
              _buildDetailRow('Doctor', procedure.doctorName ?? 'Unknown'),
              _buildDetailRow(
                'Date',
                DateFormat('MMMM d, y').format(procedure.procedureDate),
              ),
              _buildDetailRow('Outcome', procedure.outcome.toUpperCase()),
              if (procedure.billedAmount != null)
                _buildDetailRow(
                  'Billed',
                  '₹${NumberFormat('#,##0').format(procedure.billedAmount)}',
                ),
              if (procedure.icdCode != null)
                _buildDetailRow('ICD Code', procedure.icdCode!),
              if (procedure.cptCode != null)
                _buildDetailRow('CPT Code', procedure.cptCode!),
              if (procedure.notes != null) ...[
                const SizedBox(height: 8),
                Text(
                  'Notes',
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                const SizedBox(height: 4),
                Text(procedure.notes!),
              ],
              if (procedure.consumables != null &&
                  procedure.consumables!.isNotEmpty) ...[
                const SizedBox(height: 16),
                Text(
                  'Consumables Used',
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                const SizedBox(height: 8),
                ...procedure.consumables!.entries.map((e) => Padding(
                      padding: const EdgeInsets.only(bottom: 4),
                      child: Row(
                        children: [
                          const Icon(Icons.circle, size: 8),
                          const SizedBox(width: 8),
                          Text('${e.key}: ${e.value}'),
                        ],
                      ),
                    )),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDetailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(
            width: 100,
            child: Text(
              label,
              style: const TextStyle(color: Colors.grey),
            ),
          ),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }
}

/// Quick log form widget
class _QuickLogForm extends ConsumerStatefulWidget {
  final String clinicId;
  final VoidCallback onSubmit;

  const _QuickLogForm({
    required this.clinicId,
    required this.onSubmit,
  });

  @override
  ConsumerState<_QuickLogForm> createState() => _QuickLogFormState();
}

class _QuickLogFormState extends ConsumerState<_QuickLogForm> {
  final _formKey = GlobalKey<FormState>();
  String? _selectedCategory;
  String? _selectedType;
  String? _selectedDoctorId;
  String? _selectedPatientId;
  String _outcome = 'successful';
  final _notesController = TextEditingController();
  final _amountController = TextEditingController();
  final _patientSearchController = TextEditingController();
  bool _isSubmitting = false;

  List<String> _getTypesForCategory(String? category) {
    switch (category) {
      case 'Cardiology':
        return [
          'Echo',
          'ECG',
          'TMT',
          'Angiography',
          'Angioplasty',
          'Stent Placement',
          'Pacemaker',
          'Holter',
          'ABPM',
        ];
      case 'Orthopedics':
        return [
          'X-Ray Review',
          'Fracture Reduction',
          'Joint Injection',
          'PRP Therapy',
          'Surgery',
          'Joint Replacement',
          'Arthroscopy',
          'Cast Application',
        ];
      case 'Ophthalmology':
        return [
          'Eye Exam',
          'Refraction',
          'Cataract Surgery',
          'LASIK',
          'Intravitreal Injection',
          'Laser Treatment',
          'Glaucoma Surgery',
        ];
      case 'Dermatology':
        return [
          'Skin Biopsy',
          'Cryotherapy',
          'Laser Treatment',
          'Chemical Peel',
          'Botox',
          'Filler',
          'Excision',
        ];
      case 'Gastroenterology':
        return [
          'Endoscopy',
          'Colonoscopy',
          'ERCP',
          'Liver Biopsy',
          'Polypectomy',
          'Ultrasound',
        ];
      default:
        return [
          'Consultation',
          'Follow-up',
          'Procedure',
          'Minor Surgery',
          'Injection',
          'Other',
        ];
    }
  }

  @override
  void dispose() {
    _notesController.dispose();
    _amountController.dispose();
    _patientSearchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final doctorsState = ref.watch(doctorsProvider);
    final patientsState = ref.watch(patientsProvider);

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Quick Log Procedure',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),

            // Doctor dropdown
            DropdownButtonFormField<String>(
              value: _selectedDoctorId,
              decoration: const InputDecoration(
                labelText: 'Doctor',
                prefixIcon: Icon(Icons.medical_services),
                border: OutlineInputBorder(),
              ),
              items: doctorsState.doctors.map((d) {
                return DropdownMenuItem(
                  value: d.id,
                  child: Text(d.name),
                );
              }).toList(),
              onChanged: (v) => setState(() => _selectedDoctorId = v),
              validator: (v) => v == null ? 'Required' : null,
            ),
            const SizedBox(height: 12),

            // Patient search
            Autocomplete<dynamic>(
              optionsBuilder: (textValue) async {
                if (textValue.text.length < 2) return [];
                try {
                  return await ref.read(patientsProvider.notifier)
                      .searchPatients(textValue.text);
                } catch (e) {
                  return [];
                }
              },
              displayStringForOption: (option) =>
                  '${option['first_name']} ${option['last_name'] ?? ''} - ${option['phone']}',
              fieldViewBuilder: (context, controller, focusNode, onSubmitted) {
                return TextFormField(
                  controller: controller,
                  focusNode: focusNode,
                  decoration: const InputDecoration(
                    labelText: 'Patient',
                    prefixIcon: Icon(Icons.person),
                    border: OutlineInputBorder(),
                    hintText: 'Search by name or phone',
                  ),
                  validator: (v) =>
                      _selectedPatientId == null ? 'Select a patient' : null,
                );
              },
              onSelected: (option) {
                setState(() => _selectedPatientId = option['id']);
              },
            ),
            const SizedBox(height: 12),

            // Category and type row
            Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<String>(
                    value: _selectedCategory,
                    decoration: const InputDecoration(
                      labelText: 'Category',
                      border: OutlineInputBorder(),
                    ),
                    items: [
                      'Cardiology',
                      'Orthopedics',
                      'Ophthalmology',
                      'Dermatology',
                      'Gastroenterology',
                      'General',
                    ].map((c) {
                      return DropdownMenuItem(value: c, child: Text(c));
                    }).toList(),
                    onChanged: (v) {
                      setState(() {
                        _selectedCategory = v;
                        _selectedType = null;
                      });
                    },
                    validator: (v) => v == null ? 'Required' : null,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: DropdownButtonFormField<String>(
                    value: _selectedType,
                    decoration: const InputDecoration(
                      labelText: 'Type',
                      border: OutlineInputBorder(),
                    ),
                    items: _getTypesForCategory(_selectedCategory).map((t) {
                      return DropdownMenuItem(value: t, child: Text(t));
                    }).toList(),
                    onChanged: (v) => setState(() => _selectedType = v),
                    validator: (v) => v == null ? 'Required' : null,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),

            // Outcome chips
            Text('Outcome', style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                ChoiceChip(
                  label: const Text('Successful'),
                  selected: _outcome == 'successful',
                  onSelected: (_) => setState(() => _outcome = 'successful'),
                  selectedColor: Colors.green[100],
                ),
                ChoiceChip(
                  label: const Text('Partial'),
                  selected: _outcome == 'partial',
                  onSelected: (_) => setState(() => _outcome = 'partial'),
                  selectedColor: Colors.orange[100],
                ),
                ChoiceChip(
                  label: const Text('Referred'),
                  selected: _outcome == 'referred',
                  onSelected: (_) => setState(() => _outcome = 'referred'),
                  selectedColor: Colors.blue[100],
                ),
              ],
            ),
            const SizedBox(height: 12),

            // Amount
            TextFormField(
              controller: _amountController,
              decoration: const InputDecoration(
                labelText: 'Billed Amount (₹)',
                prefixIcon: Icon(Icons.currency_rupee),
                border: OutlineInputBorder(),
              ),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 12),

            // Notes
            TextFormField(
              controller: _notesController,
              decoration: const InputDecoration(
                labelText: 'Notes (optional)',
                border: OutlineInputBorder(),
              ),
              maxLines: 2,
            ),
            const SizedBox(height: 16),

            // Submit button
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _isSubmitting ? null : _submit,
                child: _isSubmitting
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Log Procedure'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isSubmitting = true);

    final result = await ref.read(proceduresProvider(widget.clinicId).notifier)
        .quickLog(
          patientId: _selectedPatientId!,
          doctorId: _selectedDoctorId!,
          category: _selectedCategory!,
          procedureType: _selectedType!,
          outcome: _outcome,
          notes: _notesController.text.isEmpty ? null : _notesController.text,
          billedAmount: _amountController.text.isEmpty
              ? null
              : double.tryParse(_amountController.text),
        );

    setState(() => _isSubmitting = false);

    if (result != null) {
      widget.onSubmit();
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Failed to log procedure'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Doctors list screen
class DoctorsScreen extends ConsumerWidget {
  const DoctorsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Doctors'),
      ),
      body: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: 5,
        itemBuilder: (context, index) {
          return Card(
            margin: const EdgeInsets.only(bottom: 12),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 30,
                    backgroundColor:
                        Theme.of(context).colorScheme.primaryContainer,
                    child: Text(
                      'D${index + 1}',
                      style: const TextStyle(fontSize: 18),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          [
                            'Dr. Priya Sharma',
                            'Dr. Rajesh Kumar',
                            'Dr. Anita Patel',
                            'Dr. Vikram Singh',
                            'Dr. Meera Reddy',
                          ][index],
                          style: Theme.of(context)
                              .textTheme
                              .titleMedium
                              ?.copyWith(fontWeight: FontWeight.bold),
                        ),
                        Text(
                          [
                            'General Medicine',
                            'Cardiology',
                            'Pediatrics',
                            'Orthopedics',
                            'Dermatology',
                          ][index],
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            Icon(
                              Icons.access_time,
                              size: 14,
                              color: Colors.grey.shade600,
                            ),
                            const SizedBox(width: 4),
                            Text(
                              '15 min slots',
                              style: Theme.of(context)
                                  .textTheme
                                  .bodySmall
                                  ?.copyWith(color: Colors.grey.shade600),
                            ),
                            const SizedBox(width: 12),
                            Icon(
                              Icons.currency_rupee,
                              size: 14,
                              color: Colors.grey.shade600,
                            ),
                            Text(
                              '${500 + index * 100}',
                              style: Theme.of(context)
                                  .textTheme
                                  .bodySmall
                                  ?.copyWith(color: Colors.grey.shade600),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  Column(
                    children: [
                      Switch(
                        value: index != 2,
                        onChanged: (value) {
                          // TODO: Toggle availability
                        },
                      ),
                      Text(
                        index != 2 ? 'Available' : 'Unavailable',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}

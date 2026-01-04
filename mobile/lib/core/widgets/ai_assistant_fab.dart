/// Floating Action Button for AI Assistant
///
/// Can be added to any screen for quick access to Practice AI Assistant

import 'package:flutter/material.dart';
import '../../features/ai_assistant/presentation/ai_chat_screen.dart';

class AIAssistantFAB extends StatelessWidget {
  const AIAssistantFAB({super.key});

  @override
  Widget build(BuildContext context) {
    return FloatingActionButton(
      onPressed: () {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => const AIChatScreen(),
          ),
        );
      },
      backgroundColor: Colors.blue,
      tooltip: 'AI Assistant',
      child: const Icon(Icons.assistant),
    );
  }
}

/// Alternative: Extended FAB with label
class AIAssistantExtendedFAB extends StatelessWidget {
  const AIAssistantExtendedFAB({super.key});

  @override
  Widget build(BuildContext context) {
    return FloatingActionButton.extended(
      onPressed: () {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => const AIChatScreen(),
          ),
        );
      },
      backgroundColor: Colors.blue,
      icon: const Icon(Icons.assistant),
      label: const Text('Ask AI'),
    );
  }
}

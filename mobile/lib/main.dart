import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:hive_flutter/hive_flutter.dart';

import 'config/app_config.dart';
import 'config/router.dart';
import 'config/theme.dart';
import 'core/providers/sync_provider.dart';
import 'core/widgets/sync_status_widget.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize Hive for local storage
  await Hive.initFlutter();

  // Initialize app configuration
  await AppConfig.initialize();

  runApp(
    const ProviderScope(
      child: DocAssistApp(),
    ),
  );
}

class DocAssistApp extends ConsumerStatefulWidget {
  const DocAssistApp({super.key});

  @override
  ConsumerState<DocAssistApp> createState() => _DocAssistAppState();
}

class _DocAssistAppState extends ConsumerState<DocAssistApp> {
  @override
  void initState() {
    super.initState();
    // Initialize offline sync service
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      final syncService = ref.read(offlineSyncServiceProvider);
      await syncService.initialize();
    });
  }

  @override
  Widget build(BuildContext context) {
    final router = ref.watch(routerProvider);

    return MaterialApp.router(
      title: 'DocAssist Practice Manager',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: ThemeMode.system,
      routerConfig: router,
      builder: (context, child) {
        return Column(
          children: [
            // Show sync status banner when needed
            const SyncStatusBanner(),
            Expanded(child: child ?? const SizedBox.shrink()),
          ],
        );
      },
    );
  }
}

import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_pdfview/flutter_pdfview.dart';
import 'package:open_file/open_file.dart';

import '../../../core/providers/reports_provider.dart';

/// Report preview screen with PDF viewer
class ReportPreviewScreen extends ConsumerStatefulWidget {
  final String reportId;
  final String filePath;

  const ReportPreviewScreen({
    super.key,
    required this.reportId,
    required this.filePath,
  });

  @override
  ConsumerState<ReportPreviewScreen> createState() =>
      _ReportPreviewScreenState();
}

class _ReportPreviewScreenState extends ConsumerState<ReportPreviewScreen> {
  int _currentPage = 0;
  int _totalPages = 0;
  bool _isReady = false;
  String? _errorMessage;

  @override
  Widget build(BuildContext context) {
    final file = File(widget.filePath);
    final isPdf = widget.filePath.toLowerCase().endsWith('.pdf');

    return Scaffold(
      appBar: AppBar(
        title: Text(_getFileName()),
        actions: [
          if (_isReady) ...[
            IconButton(
              icon: const Icon(Icons.share),
              tooltip: 'Share',
              onPressed: _shareReport,
            ),
            IconButton(
              icon: const Icon(Icons.email),
              tooltip: 'Email',
              onPressed: _emailReport,
            ),
            PopupMenuButton<String>(
              itemBuilder: (context) => [
                const PopupMenuItem(
                  value: 'open',
                  child: Row(
                    children: [
                      Icon(Icons.open_in_new, size: 18),
                      SizedBox(width: 8),
                      Text('Open with...'),
                    ],
                  ),
                ),
                const PopupMenuItem(
                  value: 'delete',
                  child: Row(
                    children: [
                      Icon(Icons.delete, size: 18, color: Colors.red),
                      SizedBox(width: 8),
                      Text('Delete', style: TextStyle(color: Colors.red)),
                    ],
                  ),
                ),
              ],
              onSelected: (value) {
                if (value == 'open') {
                  _openWithExternalApp();
                } else if (value == 'delete') {
                  _confirmDelete();
                }
              },
            ),
          ],
        ],
      ),
      body: Column(
        children: [
          // Page counter for PDFs
          if (isPdf && _isReady && _totalPages > 0)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(8),
              color: Colors.grey.shade200,
              child: Text(
                'Page ${_currentPage + 1} of $_totalPages',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ),

          // Content
          Expanded(
            child: _buildContent(file, isPdf),
          ),
        ],
      ),
    );
  }

  Widget _buildContent(File file, bool isPdf) {
    if (!file.existsSync()) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 64, color: Colors.red),
            const SizedBox(height: 16),
            const Text('File not found'),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Go Back'),
            ),
          ],
        ),
      );
    }

    if (isPdf) {
      return _buildPdfViewer(file);
    } else {
      return _buildGenericViewer(file);
    }
  }

  Widget _buildPdfViewer(File file) {
    return PDFView(
      filePath: file.path,
      enableSwipe: true,
      swipeHorizontal: false,
      autoSpacing: true,
      pageFling: true,
      pageSnap: true,
      defaultPage: _currentPage,
      fitPolicy: FitPolicy.WIDTH,
      onRender: (pages) {
        setState(() {
          _totalPages = pages ?? 0;
          _isReady = true;
        });
      },
      onError: (error) {
        setState(() {
          _errorMessage = error.toString();
          _isReady = false;
        });
      },
      onPageError: (page, error) {
        setState(() {
          _errorMessage = 'Error on page $page: $error';
        });
      },
      onViewCreated: (PDFViewController pdfViewController) {
        // PDF view controller available if needed
      },
      onPageChanged: (int? page, int? total) {
        setState(() {
          _currentPage = page ?? 0;
          _totalPages = total ?? 0;
        });
      },
    );
  }

  Widget _buildGenericViewer(File file) {
    final extension = widget.filePath.split('.').last.toUpperCase();

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              _getFileIcon(extension),
              size: 96,
              color: Theme.of(context).colorScheme.primary,
            ),
            const SizedBox(height: 24),
            Text(
              _getFileName(),
              style: Theme.of(context).textTheme.titleLarge,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              '$extension File',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.grey,
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              _formatFileSize(file.lengthSync()),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.grey.shade600,
                  ),
            ),
            const SizedBox(height: 32),
            ElevatedButton.icon(
              onPressed: _openWithExternalApp,
              icon: const Icon(Icons.open_in_new),
              label: const Text('Open with External App'),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: _shareReport,
              icon: const Icon(Icons.share),
              label: const Text('Share File'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _shareReport() async {
    await ref.read(reportsProvider.notifier).shareReport(
          widget.filePath,
          reportName: _getFileName(),
        );
  }

  Future<void> _emailReport() async {
    final emailController = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Email Report'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Send this report via email'),
            const SizedBox(height: 16),
            TextField(
              controller: emailController,
              decoration: const InputDecoration(
                labelText: 'Recipient Email',
                hintText: 'email@example.com',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.email),
              ),
              keyboardType: TextInputType.emailAddress,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Send'),
          ),
        ],
      ),
    );

    if (confirmed == true && emailController.text.isNotEmpty) {
      await ref.read(reportsProvider.notifier).emailReport(
            reportId: widget.reportId,
            recipients: [emailController.text],
          );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Report sent via email'),
            backgroundColor: Colors.green,
          ),
        );
      }
    }
  }

  Future<void> _openWithExternalApp() async {
    try {
      final result = await OpenFile.open(widget.filePath);
      if (result.type != ResultType.done && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Could not open file: ${result.message}'),
            backgroundColor: Colors.orange,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error opening file: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _confirmDelete() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Report'),
        content: const Text(
          'Are you sure you want to delete this report? This will remove the downloaded file from your device.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        // Delete local file
        final file = File(widget.filePath);
        if (file.existsSync()) {
          await file.delete();
        }

        // Delete from backend
        await ref.read(reportsProvider.notifier).deleteReport(widget.reportId);

        if (mounted) {
          Navigator.pop(context);
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Report deleted'),
              backgroundColor: Colors.red,
            ),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Error deleting report: $e'),
              backgroundColor: Colors.red,
            ),
          );
        }
      }
    }
  }

  String _getFileName() {
    return widget.filePath.split('/').last;
  }

  IconData _getFileIcon(String extension) {
    switch (extension.toLowerCase()) {
      case 'pdf':
        return Icons.picture_as_pdf;
      case 'xlsx':
      case 'xls':
      case 'excel':
        return Icons.table_chart;
      case 'csv':
        return Icons.grid_on;
      default:
        return Icons.insert_drive_file;
    }
  }

  String _formatFileSize(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }
}

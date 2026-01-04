import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

/// Documents List Screen
///
/// Phase 10: Document Scanner & OCR
///
/// Features:
/// - View all scanned documents for a patient
/// - Filter by document type
/// - View OCR extracted text
/// - Download/share documents
class DocumentsListScreen extends StatefulWidget {
  final String patientId;
  final String patientName;

  const DocumentsListScreen({
    super.key,
    required this.patientId,
    required this.patientName,
  });

  @override
  State<DocumentsListScreen> createState() => _DocumentsListScreenState();
}

class _DocumentsListScreenState extends State<DocumentsListScreen> {
  String? _selectedType;
  bool _showProcessedOnly = false;

  // Mock data - Replace with actual API call
  final List<DocumentItem> _documents = [
    DocumentItem(
      id: '1',
      filename: 'blood_test_report.jpg',
      type: 'lab_report',
      scanDate: DateTime.now().subtract(const Duration(days: 2)),
      isProcessed: true,
      pageCount: 1,
      fileSize: 245000,
    ),
    DocumentItem(
      id: '2',
      filename: 'prescription_dr_sharma.jpg',
      type: 'prescription',
      scanDate: DateTime.now().subtract(const Duration(days: 5)),
      isProcessed: true,
      pageCount: 1,
      fileSize: 180000,
    ),
    DocumentItem(
      id: '3',
      filename: 'xray_chest.jpg',
      type: 'radiology',
      scanDate: DateTime.now().subtract(const Duration(days: 10)),
      isProcessed: false,
      pageCount: 2,
      fileSize: 520000,
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final filteredDocs = _getFilteredDocuments();

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Documents'),
            Text(
              widget.patientName,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
        actions: [
          PopupMenuButton<String>(
            icon: const Icon(Icons.filter_list),
            onSelected: (value) {
              setState(() {
                _selectedType = value == 'all' ? null : value;
              });
            },
            itemBuilder: (context) => [
              const PopupMenuItem(
                value: 'all',
                child: Text('All Types'),
              ),
              const PopupMenuItem(
                value: 'lab_report',
                child: Text('Lab Reports'),
              ),
              const PopupMenuItem(
                value: 'prescription',
                child: Text('Prescriptions'),
              ),
              const PopupMenuItem(
                value: 'radiology',
                child: Text('Radiology'),
              ),
              const PopupMenuItem(
                value: 'other',
                child: Text('Other'),
              ),
            ],
          ),
        ],
      ),
      body: Column(
        children: [
          // Filter Chip
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Row(
              children: [
                FilterChip(
                  label: const Text('Processed Only'),
                  selected: _showProcessedOnly,
                  onSelected: (selected) {
                    setState(() {
                      _showProcessedOnly = selected;
                    });
                  },
                ),
                const SizedBox(width: 8),
                if (_selectedType != null)
                  Chip(
                    label: Text(_formatDocumentType(_selectedType!)),
                    onDeleted: () {
                      setState(() {
                        _selectedType = null;
                      });
                    },
                  ),
              ],
            ),
          ),

          // Documents List
          Expanded(
            child: filteredDocs.isEmpty
                ? _buildEmptyState()
                : ListView.builder(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    itemCount: filteredDocs.length,
                    itemBuilder: (context, index) {
                      return _buildDocumentCard(filteredDocs[index]);
                    },
                  ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _navigateToScanner(context),
        icon: const Icon(Icons.document_scanner),
        label: const Text('Scan New'),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.description_outlined,
            size: 100,
            color: Colors.grey[400],
          ),
          const SizedBox(height: 16),
          Text(
            _selectedType != null || _showProcessedOnly
                ? 'No documents match your filters'
                : 'No documents yet',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: Colors.grey[600],
                ),
          ),
          const SizedBox(height: 8),
          Text(
            'Tap "Scan New" to add documents',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Colors.grey[500],
                ),
          ),
        ],
      ),
    );
  }

  Widget _buildDocumentCard(DocumentItem doc) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: () => _viewDocument(doc),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header Row
              Row(
                children: [
                  // Document Icon
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: _getDocumentTypeColor(doc.type).withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(
                      _getDocumentTypeIcon(doc.type),
                      color: _getDocumentTypeColor(doc.type),
                      size: 28,
                    ),
                  ),
                  const SizedBox(width: 16),

                  // Document Info
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          doc.filename,
                          style: const TextStyle(
                            fontWeight: FontWeight.w600,
                            fontSize: 16,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            Text(
                              _formatDocumentType(doc.type),
                              style: TextStyle(
                                fontSize: 13,
                                color: Colors.grey[600],
                              ),
                            ),
                            const SizedBox(width: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 8,
                                vertical: 2,
                              ),
                              decoration: BoxDecoration(
                                color: doc.isProcessed
                                    ? Colors.green.withOpacity(0.1)
                                    : Colors.orange.withOpacity(0.1),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Text(
                                doc.isProcessed ? 'Processed' : 'Pending',
                                style: TextStyle(
                                  fontSize: 11,
                                  color: doc.isProcessed
                                      ? Colors.green[700]
                                      : Colors.orange[700],
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),

                  // More Options
                  IconButton(
                    icon: const Icon(Icons.more_vert),
                    onPressed: () => _showDocumentOptions(doc),
                  ),
                ],
              ),

              const SizedBox(height: 12),
              const Divider(height: 1),
              const SizedBox(height: 12),

              // Footer Info
              Row(
                children: [
                  Icon(Icons.calendar_today, size: 14, color: Colors.grey[600]),
                  const SizedBox(width: 4),
                  Text(
                    DateFormat('MMM dd, yyyy').format(doc.scanDate),
                    style: TextStyle(fontSize: 13, color: Colors.grey[600]),
                  ),
                  const SizedBox(width: 16),
                  Icon(Icons.pages, size: 14, color: Colors.grey[600]),
                  const SizedBox(width: 4),
                  Text(
                    '${doc.pageCount} page${doc.pageCount > 1 ? 's' : ''}',
                    style: TextStyle(fontSize: 13, color: Colors.grey[600]),
                  ),
                  const SizedBox(width: 16),
                  Icon(Icons.file_present, size: 14, color: Colors.grey[600]),
                  const SizedBox(width: 4),
                  Text(
                    _formatFileSize(doc.fileSize),
                    style: TextStyle(fontSize: 13, color: Colors.grey[600]),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  List<DocumentItem> _getFilteredDocuments() {
    return _documents.where((doc) {
      if (_selectedType != null && doc.type != _selectedType) {
        return false;
      }
      if (_showProcessedOnly && !doc.isProcessed) {
        return false;
      }
      return true;
    }).toList();
  }

  void _navigateToScanner(BuildContext context) {
    // TODO: Navigate to DocumentScannerScreen
    // Navigator.push(
    //   context,
    //   MaterialPageRoute(
    //     builder: (context) => DocumentScannerScreen(
    //       patientId: widget.patientId,
    //       patientName: widget.patientName,
    //     ),
    //   ),
    // );
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Navigate to Document Scanner')),
    );
  }

  void _viewDocument(DocumentItem doc) {
    // TODO: Navigate to document viewer
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('View document: ${doc.filename}')),
    );
  }

  void _showDocumentOptions(DocumentItem doc) {
    showModalBottomSheet(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.text_fields),
              title: const Text('View OCR Text'),
              enabled: doc.isProcessed,
              onTap: () {
                Navigator.pop(context);
                _viewOCRText(doc);
              },
            ),
            ListTile(
              leading: const Icon(Icons.download),
              title: const Text('Download'),
              onTap: () {
                Navigator.pop(context);
                // TODO: Download document
              },
            ),
            ListTile(
              leading: const Icon(Icons.share),
              title: const Text('Share'),
              onTap: () {
                Navigator.pop(context);
                // TODO: Share document
              },
            ),
            ListTile(
              leading: const Icon(Icons.delete, color: Colors.red),
              title: const Text('Delete', style: TextStyle(color: Colors.red)),
              onTap: () {
                Navigator.pop(context);
                _confirmDelete(doc);
              },
            ),
          ],
        ),
      ),
    );
  }

  void _viewOCRText(DocumentItem doc) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Extracted Text'),
        content: SingleChildScrollView(
          child: Text(
            doc.isProcessed
                ? 'OCR text would appear here...\n\nPatient Name: John Doe\nTest Date: 2026-01-02\nHemoglobin: 14.5 g/dL'
                : 'Document not yet processed',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  void _confirmDelete(DocumentItem doc) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Document?'),
        content: Text('Are you sure you want to delete "${doc.filename}"?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              setState(() {
                _documents.remove(doc);
              });
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Document deleted')),
              );
            },
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }

  // ========== Utilities ==========

  String _formatDocumentType(String type) {
    return type
        .split('_')
        .map((word) => word[0].toUpperCase() + word.substring(1))
        .join(' ');
  }

  String _formatFileSize(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }

  IconData _getDocumentTypeIcon(String type) {
    switch (type) {
      case 'lab_report':
      case 'test_result':
        return Icons.biotech;
      case 'prescription':
        return Icons.medication;
      case 'radiology':
      case 'imaging':
        return Icons.medical_services;
      case 'ecg_report':
      case 'echo_report':
        return Icons.monitor_heart;
      default:
        return Icons.description;
    }
  }

  Color _getDocumentTypeColor(String type) {
    switch (type) {
      case 'lab_report':
      case 'test_result':
        return Colors.blue;
      case 'prescription':
        return Colors.green;
      case 'radiology':
      case 'imaging':
        return Colors.purple;
      case 'ecg_report':
      case 'echo_report':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }
}

// ========== Models ==========

class DocumentItem {
  final String id;
  final String filename;
  final String type;
  final DateTime scanDate;
  final bool isProcessed;
  final int pageCount;
  final int fileSize;

  DocumentItem({
    required this.id,
    required this.filename,
    required this.type,
    required this.scanDate,
    required this.isProcessed,
    required this.pageCount,
    required this.fileSize,
  });
}

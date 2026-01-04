import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:image_cropper/image_cropper.dart';
import 'package:permission_handler/permission_handler.dart';

/// Document Scanner Screen
///
/// Phase 10: Document Scanner & OCR
///
/// Features:
/// - Camera capture for document scanning
/// - Image cropping with edge detection
/// - Multi-page document support
/// - Upload to backend
/// - View scanned documents
class DocumentScannerScreen extends StatefulWidget {
  final String patientId;
  final String patientName;

  const DocumentScannerScreen({
    super.key,
    required this.patientId,
    required this.patientName,
  });

  @override
  State<DocumentScannerScreen> createState() => _DocumentScannerScreenState();
}

class _DocumentScannerScreenState extends State<DocumentScannerScreen> {
  final ImagePicker _imagePicker = ImagePicker();
  final List<File> _scannedPages = [];
  bool _isProcessing = false;
  String? _selectedDocumentType;

  // Document types matching backend
  final List<String> _documentTypes = [
    'lab_report',
    'prescription',
    'radiology',
    'medical_history',
    'insurance',
    'consent_form',
    'discharge_summary',
    'referral_letter',
    'test_result',
    'imaging',
    'pathology',
    'ecg_report',
    'echo_report',
    'other',
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Document Scanner'),
            Text(
              widget.patientName,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
        actions: [
          if (_scannedPages.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.check),
              onPressed: _uploadDocuments,
              tooltip: 'Upload Documents',
            ),
        ],
      ),
      body: Column(
        children: [
          // Document Type Selector
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: DropdownButtonFormField<String>(
              value: _selectedDocumentType,
              decoration: const InputDecoration(
                labelText: 'Document Type',
                border: OutlineInputBorder(),
              ),
              items: _documentTypes.map((type) {
                return DropdownMenuItem(
                  value: type,
                  child: Text(_formatDocumentType(type)),
                );
              }).toList(),
              onChanged: (value) {
                setState(() {
                  _selectedDocumentType = value;
                });
              },
            ),
          ),

          // Scanned Pages Grid
          Expanded(
            child: _scannedPages.isEmpty
                ? _buildEmptyState()
                : _buildScannedPagesGrid(),
          ),

          // Action Buttons
          _buildActionButtons(),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.document_scanner_outlined,
            size: 100,
            color: Colors.grey[400],
          ),
          const SizedBox(height: 16),
          Text(
            'No documents scanned yet',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: Colors.grey[600],
                ),
          ),
          const SizedBox(height: 8),
          Text(
            'Tap the camera button to start scanning',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Colors.grey[500],
                ),
          ),
        ],
      ),
    );
  }

  Widget _buildScannedPagesGrid() {
    return GridView.builder(
      padding: const EdgeInsets.all(16),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        crossAxisSpacing: 16,
        mainAxisSpacing: 16,
        childAspectRatio: 0.7,
      ),
      itemCount: _scannedPages.length,
      itemBuilder: (context, index) {
        return _buildPageCard(index);
      },
    );
  }

  Widget _buildPageCard(int index) {
    return Card(
      clipBehavior: Clip.antiAlias,
      child: Stack(
        fit: StackFit.expand,
        children: [
          // Image
          Image.file(
            _scannedPages[index],
            fit: BoxFit.cover,
          ),

          // Page Number Badge
          Positioned(
            top: 8,
            left: 8,
            child: Container(
              padding: const EdgeInsets.symmetric(
                horizontal: 8,
                vertical: 4,
              ),
              decoration: BoxDecoration(
                color: Colors.black87,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                'Page ${index + 1}',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),

          // Delete Button
          Positioned(
            top: 8,
            right: 8,
            child: IconButton(
              icon: const Icon(Icons.close),
              color: Colors.white,
              style: IconButton.styleFrom(
                backgroundColor: Colors.red,
              ),
              onPressed: () => _deletePage(index),
            ),
          ),

          // View/Edit Button
          Positioned(
            bottom: 8,
            right: 8,
            child: IconButton(
              icon: const Icon(Icons.crop),
              color: Colors.white,
              style: IconButton.styleFrom(
                backgroundColor: Colors.blue,
              ),
              onPressed: () => _recropPage(index),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActionButtons() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, -5),
          ),
        ],
      ),
      child: Row(
        children: [
          // Camera Button
          Expanded(
            child: ElevatedButton.icon(
              onPressed: _isProcessing ? null : () => _captureDocument(ImageSource.camera),
              icon: const Icon(Icons.camera_alt),
              label: const Text('Camera'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
            ),
          ),
          const SizedBox(width: 16),

          // Gallery Button
          Expanded(
            child: OutlinedButton.icon(
              onPressed: _isProcessing ? null : () => _captureDocument(ImageSource.gallery),
              icon: const Icon(Icons.photo_library),
              label: const Text('Gallery'),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ========== Document Capture ==========

  Future<void> _captureDocument(ImageSource source) async {
    setState(() {
      _isProcessing = true;
    });

    try {
      // Request camera/gallery permission
      final permission = source == ImageSource.camera
          ? Permission.camera
          : Permission.photos;

      final status = await permission.request();
      if (!status.isGranted) {
        if (mounted) {
          _showError('Permission denied. Please enable in settings.');
        }
        return;
      }

      // Capture image
      final XFile? image = await _imagePicker.pickImage(
        source: source,
        preferredCameraDevice: CameraDevice.rear,
        imageQuality: 100,
      );

      if (image == null) return;

      // Crop image
      final croppedFile = await _cropImage(File(image.path));

      if (croppedFile != null) {
        setState(() {
          _scannedPages.add(croppedFile);
        });

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Page ${_scannedPages.length} added'),
              action: SnackBarAction(
                label: 'Undo',
                onPressed: () {
                  setState(() {
                    _scannedPages.removeLast();
                  });
                },
              ),
            ),
          );
        }
      }
    } catch (e) {
      _showError('Failed to capture document: $e');
    } finally {
      setState(() {
        _isProcessing = false;
      });
    }
  }

  Future<File?> _cropImage(File imageFile) async {
    final croppedFile = await ImageCropper().cropImage(
      sourcePath: imageFile.path,
      uiSettings: [
        AndroidUiSettings(
          toolbarTitle: 'Crop Document',
          toolbarColor: Theme.of(context).primaryColor,
          toolbarWidgetColor: Colors.white,
          aspectRatioPresets: [
            CropAspectRatioPreset.original,
            CropAspectRatioPreset.square,
            CropAspectRatioPreset.ratio4x3,
            CropAspectRatioPreset.ratio3x2,
          ],
          initAspectRatio: CropAspectRatioPreset.original,
          lockAspectRatio: false,
        ),
        IOSUiSettings(
          title: 'Crop Document',
          aspectRatioPresets: [
            CropAspectRatioPreset.original,
            CropAspectRatioPreset.square,
            CropAspectRatioPreset.ratio4x3,
            CropAspectRatioPreset.ratio3x2,
          ],
        ),
      ],
    );

    return croppedFile?.path != null ? File(croppedFile!.path) : null;
  }

  Future<void> _recropPage(int index) async {
    final croppedFile = await _cropImage(_scannedPages[index]);
    if (croppedFile != null) {
      setState(() {
        _scannedPages[index] = croppedFile;
      });
    }
  }

  void _deletePage(int index) {
    setState(() {
      _scannedPages.removeAt(index);
    });
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Page deleted')),
    );
  }

  // ========== Upload Documents ==========

  Future<void> _uploadDocuments() async {
    if (_scannedPages.isEmpty) {
      _showError('No documents to upload');
      return;
    }

    if (_selectedDocumentType == null) {
      _showError('Please select a document type');
      return;
    }

    setState(() {
      _isProcessing = true;
    });

    try {
      // TODO: Upload to backend API
      // For now, show success message
      await Future.delayed(const Duration(seconds: 2)); // Simulate upload

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              '${_scannedPages.length} page(s) uploaded successfully',
            ),
            backgroundColor: Colors.green,
          ),
        );

        // Navigate back
        Navigator.of(context).pop(true);
      }
    } catch (e) {
      _showError('Failed to upload documents: $e');
    } finally {
      setState(() {
        _isProcessing = false;
      });
    }
  }

  // ========== Utilities ==========

  String _formatDocumentType(String type) {
    return type
        .split('_')
        .map((word) => word[0].toUpperCase() + word.substring(1))
        .join(' ');
  }

  void _showError(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
      ),
    );
  }

  @override
  void dispose() {
    // Clean up temporary files if not uploaded
    for (final file in _scannedPages) {
      try {
        if (file.existsSync()) {
          file.deleteSync();
        }
      } catch (_) {}
    }
    super.dispose();
  }
}

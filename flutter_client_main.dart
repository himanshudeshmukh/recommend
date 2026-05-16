import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'package:image_picker/image_picker.dart';

void main() => runApp(const FashionpediaApp());

// ═══════════════════════════════════════════════════════════════════════════
// MAIN APP — Flutter client for the Fashionpedia FastAPI service.
//
// This app provides 3 tabs:
//   Tab 1: Health Check   → GET  /api/v1/health
//   Tab 2: Image Analysis → POST /api/v1/images/analyze
//   Tab 3: Outfit Recommend → POST /api/v1/outfits/recommend
// ═══════════════════════════════════════════════════════════════════════════

class FashionpediaApp extends StatelessWidget {
  const FashionpediaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Fashionpedia Client',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: Colors.deepPurple,
        useMaterial3: true,
      ),
      home: const HomePage(),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// HOME PAGE — Tab-based navigation between the 3 endpoints.
// ═══════════════════════════════════════════════════════════════════════════

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  int _currentTab = 0;

  // ── CHANGE THIS to your server's address ──────────────────────────────
  // For local testing on Windows/Mac: http://localhost:8000
  // For Android emulator use: http://10.0.2.2:8000
  // For iOS simulator use: http://localhost:8000
  // For real device use your machine's local IP: http://192.168.x.x:8000
  static const String baseUrl = 'http://localhost:8000/api/v1';

  final List<Widget> _pages = [
    const HealthCheckTab(baseUrl: baseUrl),
    const ImageAnalysisTab(baseUrl: baseUrl),
    const OutfitRecommendTab(baseUrl: baseUrl),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('👗 Fashionpedia API Client'),
        centerTitle: true,
        backgroundColor: Colors.deepPurple,
        foregroundColor: Colors.white,
      ),
      body: _pages[_currentTab],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentTab,
        onDestinationSelected: (i) => setState(() => _currentTab = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.favorite), label: 'Health'),
          NavigationDestination(icon: Icon(Icons.image), label: 'Analyze'),
          NavigationDestination(icon: Icon(Icons.checkroom), label: 'Recommend'),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// TAB 1: HEALTH CHECK
// Calls: GET /api/v1/health
// Expected response: {"status": "healthy", "service": "fashionpedia-api"}
// ═══════════════════════════════════════════════════════════════════════════

class HealthCheckTab extends StatefulWidget {
  final String baseUrl;
  const HealthCheckTab({super.key, required this.baseUrl});

  @override
  State<HealthCheckTab> createState() => _HealthCheckTabState();
}

class _HealthCheckTabState extends State<HealthCheckTab> {
  String _result = 'Tap the button to check service health.';
  bool _loading = false;

  Future<void> _checkHealth() async {
    setState(() {
      _loading = true;
      _result = 'Checking...';
    });

    try {
      final response = await http.get(
        Uri.parse('${widget.baseUrl}/health'),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        _result = '✅ Status: ${data['status']}\n'
            '🏷️ Service: ${data['service']}';
      } else {
        _result = '❌ HTTP ${response.statusCode}\n${response.body}';
      }
    } catch (e) {
      _result = '❌ Connection error:\n$e\n\nMake sure the server is running at:\n${widget.baseUrl}';
    }

    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.monitor_heart, size: 64, color: Colors.green),
          const SizedBox(height: 16),
          const Text('Health Check', style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          const Text('GET /api/v1/health', style: TextStyle(color: Colors.grey)),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: _loading ? null : _checkHealth,
            icon: const Icon(Icons.refresh),
            label: const Text('Check Health'),
          ),
          const SizedBox(height: 24),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.grey.shade100,
              borderRadius: BorderRadius.circular(12),
            ),
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : SingleChildScrollView(
                    child: Text(_result, style: const TextStyle(fontSize: 14, fontFamily: 'monospace')),
                  ),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// TAB 2: IMAGE ANALYSIS
// Calls: POST /api/v1/images/analyze (multipart form with image + fields)
//
// Flow:
//   1. User picks an image from gallery/camera
//   2. User optionally fills in occasion, weather, gender
//   3. App sends multipart POST with image + form fields
//   4. App displays detected items, style prediction, colors
// ═══════════════════════════════════════════════════════════════════════════

class ImageAnalysisTab extends StatefulWidget {
  final String baseUrl;
  const ImageAnalysisTab({super.key, required this.baseUrl});

  @override
  State<ImageAnalysisTab> createState() => _ImageAnalysisTabState();
}

class _ImageAnalysisTabState extends State<ImageAnalysisTab> {
  final _occasionCtrl = TextEditingController(text: 'office');
  final _weatherCtrl = TextEditingController(text: 'sunny');
  final _genderCtrl = TextEditingController(text: 'female');
  final _tempCtrl = TextEditingController(text: '22');

  XFile? _pickedImage;
  String _result = 'Pick an image and tap "Analyze".';
  bool _loading = false;

  Future<void> _pickImage() async {
    final picker = ImagePicker();
    final image = await picker.pickImage(source: ImageSource.gallery, imageQuality: 85);
    if (image != null) {
      setState(() {
        _pickedImage = image;
        _result = 'Image selected: ${image.name}\nTap "Analyze" to send.';
      });
    }
  }

  Future<void> _analyzeImage() async {
    if (_pickedImage == null) {
      setState(() => _result = '⚠️ Please pick an image first.');
      return;
    }

    setState(() {
      _loading = true;
      _result = '🔄 Uploading and analyzing...';
    });

    try {
      final uri = Uri.parse('${widget.baseUrl}/images/analyze');
      final request = http.MultipartRequest('POST', uri);

      // Attach the image file with proper content type
      final imageFile = http.MultipartFile.fromPath(
        'image',
        _pickedImage!.path,
        contentType: MediaType('image', 'jpeg'),
      );
      request.files.add(imageFile);

      // Attach optional form fields
      if (_occasionCtrl.text.isNotEmpty) request.fields['occasion'] = _occasionCtrl.text;
      if (_weatherCtrl.text.isNotEmpty) request.fields['weather'] = _weatherCtrl.text;
      if (_genderCtrl.text.isNotEmpty) request.fields['gender'] = _genderCtrl.text;
      if (_tempCtrl.text.isNotEmpty) request.fields['temperature_celsius'] = _tempCtrl.text;

      // Send request with timeout
      final streamedResponse = await request.send().timeout(const Duration(seconds: 60));
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);

        // Extract key results for display
        final detections = data['fashionpedia_detections'] as List? ?? [];
        final prediction = data['outfit_prediction'] as Map? ?? {};
        final quality = data['quality_metadata'] as Map? ?? {};

        final buffer = StringBuffer();
        buffer.writeln('✅ Analysis Complete!\n');
        buffer.writeln('📊 Style: ${prediction['predicted_style_label'] ?? 'N/A'}');
        buffer.writeln('🎯 Occasion fit: ${prediction['occasion_alignment'] ?? 'N/A'}');
        buffer.writeln('🌤️ Weather fit: ${prediction['weather_alignment'] ?? 'N/A'}');
        
        final confidence = prediction['confidence'];
        if (confidence != null) {
          buffer.writeln('💯 Confidence: ${(confidence * 100).toStringAsFixed(0)}%');
        }
        buffer.writeln('\n👕 Detected ${detections.length} item(s):');
        
        for (final item in detections.take(8)) {
          final label = item['label'] ?? 'Unknown';
          final conf = item['confidence'] ?? 0.0;
          buffer.writeln('  • $label (${(conf * 100).toStringAsFixed(0)}%)');
        }
        
        if (detections.length > 8) {
          buffer.writeln('  ... and ${detections.length - 8} more');
        }

        final colors = quality['dominant_colors'] as List? ?? [];
        if (colors.isNotEmpty) {
          buffer.writeln('\n🎨 Dominant colors:');
          for (final color in colors.take(5)) {
            final name = color['name'] ?? 'Unknown';
            final hex = color['hex'] ?? '#000000';
            buffer.writeln('  • $name ($hex)');
          }
        }

        final warnings = quality['quality_warnings'] as List? ?? [];
        if (warnings.isNotEmpty) {
          buffer.writeln('\n⚠️ Warnings:');
          for (final w in warnings) {
            buffer.writeln('  • $w');
          }
        }

        _result = buffer.toString();
      } else {
        final data = jsonDecode(response.body);
        _result = '❌ HTTP ${response.statusCode}\n'
            'Error: ${data['error'] ?? data['detail'] ?? response.body}';
      }
    } catch (e) {
      _result = '❌ Error:\n$e';
    }

    if (mounted) setState(() => _loading = false);
  }

  @override
  void dispose() {
    _occasionCtrl.dispose();
    _weatherCtrl.dispose();
    _genderCtrl.dispose();
    _tempCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header card
          Card(
            elevation: 2,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  const Text('📸 Image Analysis', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 4),
                  const Text('POST /api/v1/images/analyze', style: TextStyle(color: Colors.grey, fontSize: 12)),
                  const SizedBox(height: 16),
                  ElevatedButton.icon(
                    onPressed: _pickImage,
                    icon: const Icon(Icons.photo_library),
                    label: Text(_pickedImage == null ? 'Pick Image' : '📷 ${_pickedImage!.name}'),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),

          // Form fields
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Context (optional)', style: TextStyle(fontWeight: FontWeight.bold)),
                  const SizedBox(height: 12),
                  Row(children: [
                    Expanded(
                      child: TextField(
                        controller: _occasionCtrl,
                        decoration: const InputDecoration(
                          labelText: 'Occasion',
                          border: OutlineInputBorder(),
                          isDense: true,
                          hintText: 'e.g. office, party',
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: TextField(
                        controller: _weatherCtrl,
                        decoration: const InputDecoration(
                          labelText: 'Weather',
                          border: OutlineInputBorder(),
                          isDense: true,
                          hintText: 'e.g. sunny, rainy',
                        ),
                      ),
                    ),
                  ]),
                  const SizedBox(height: 8),
                  Row(children: [
                    Expanded(
                      child: TextField(
                        controller: _genderCtrl,
                        decoration: const InputDecoration(
                          labelText: 'Gender',
                          border: OutlineInputBorder(),
                          isDense: true,
                          hintText: 'e.g. male, female',
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: TextField(
                        controller: _tempCtrl,
                        decoration: const InputDecoration(
                          labelText: 'Temp (°C)',
                          border: OutlineInputBorder(),
                          isDense: true,
                        ),
                        keyboardType: TextInputType.number,
                      ),
                    ),
                  ]),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),

          // Analyze button
          ElevatedButton.icon(
            onPressed: _loading ? null : _analyzeImage,
            icon: const Icon(Icons.search),
            label: const Text('Analyze Image'),
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.all(16),
              backgroundColor: Colors.deepPurple,
              foregroundColor: Colors.white,
            ),
          ),
          const SizedBox(height: 12),

          // Results
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.grey.shade100,
              borderRadius: BorderRadius.circular(12),
            ),
            child: _loading
                ? const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator()))
                : SingleChildScrollView(child: Text(_result, style: const TextStyle(fontSize: 13, fontFamily: 'monospace'))),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// TAB 3: OUTFIT RECOMMENDATION
// Calls: POST /api/v1/outfits/recommend (multipart form, image optional)
//
// Flow:
//   1. User fills in occasion (required), weather, gender, preferences
//   2. User optionally picks a reference image
//   3. App sends multipart POST with form fields + optional image
//   4. App displays ranked outfit recommendations
// ═══════════════════════════════════════════════════════════════════════════

class OutfitRecommendTab extends StatefulWidget {
  final String baseUrl;
  const OutfitRecommendTab({super.key, required this.baseUrl});

  @override
  State<OutfitRecommendTab> createState() => _OutfitRecommendTabState();
}

class _OutfitRecommendTabState extends State<OutfitRecommendTab> {
  final _occasionCtrl = TextEditingController(text: 'office');
  final _weatherCtrl = TextEditingController(text: 'rainy');
  final _genderCtrl = TextEditingController(text: 'male');
  final _tempCtrl = TextEditingController(text: '16');
  final _styleCtrl = TextEditingController(text: 'minimal, classic');
  final _colorCtrl = TextEditingController(text: 'navy, charcoal');
  final _avoidCtrl = TextEditingController(text: 'shorts');

  XFile? _refImage;
  String _result = 'Fill in the occasion and tap "Get Recommendations".';
  bool _loading = false;

  Future<void> _pickRefImage() async {
    final picker = ImagePicker();
    final image = await picker.pickImage(source: ImageSource.gallery, imageQuality: 85);
    if (image != null) {
      setState(() => _refImage = image);
    }
  }

  Future<void> _recommend() async {
    if (_occasionCtrl.text.isEmpty) {
      setState(() => _result = '⚠️ Occasion is required (e.g., office, party, beach).');
      return;
    }

    setState(() {
      _loading = true;
      _result = '🔄 Generating recommendations...';
    });

    try {
      final uri = Uri.parse('${widget.baseUrl}/outfits/recommend');
      final request = http.MultipartRequest('POST', uri);

      // Required field
      request.fields['occasion'] = _occasionCtrl.text;

      // Optional fields
      if (_weatherCtrl.text.isNotEmpty) request.fields['weather'] = _weatherCtrl.text;
      if (_genderCtrl.text.isNotEmpty) request.fields['gender'] = _genderCtrl.text;
      if (_tempCtrl.text.isNotEmpty) request.fields['temperature_celsius'] = _tempCtrl.text;
      if (_styleCtrl.text.isNotEmpty) request.fields['style_preferences'] = _styleCtrl.text;
      if (_colorCtrl.text.isNotEmpty) request.fields['color_preferences'] = _colorCtrl.text;
      if (_avoidCtrl.text.isNotEmpty) request.fields['avoid_items'] = _avoidCtrl.text;

      // Optional reference image
      if (_refImage != null) {
        final imageFile = http.MultipartFile.fromPath(
          'image',
          _refImage!.path,
          contentType: MediaType('image', 'jpeg'),
        );
        request.files.add(imageFile);
      }

      final streamedResponse = await request.send().timeout(const Duration(seconds: 60));
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final recommendations = data['recommendations'] as List? ?? [];

        final buffer = StringBuffer();
        buffer.writeln('✅ ${recommendations.length} Outfit(s) Recommended!\n');

        for (final rec in recommendations) {
          buffer.writeln('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
          buffer.writeln('#${rec['rank']} ${rec['title']}');
          buffer.writeln('   Style: ${rec['style_label'] ?? 'N/A'}');
          
          final conf = rec['confidence'];
          if (conf != null) {
            buffer.writeln('   Confidence: ${(conf * 100).toStringAsFixed(0)}%');
          }
          
          final primary = rec['primary_items'] as List? ?? [];
          buffer.writeln('   👕 Items: ${primary.join(', ')}');
          
          final optional = rec['optional_items'] as List? ?? [];
          buffer.writeln('   👜 Extras: ${optional.join(', ')}');
          
          final colors = rec['palette_direction'] as List? ?? [];
          buffer.writeln('   🎨 Colors: ${colors.join(', ')}');
          
          final reasoning = rec['reasoning'] as List? ?? [];
          if (reasoning.isNotEmpty) {
            buffer.writeln('   💡 Why: ${reasoning.first}');
          }
          buffer.writeln('');
        }

        final deprioritized = data['deprioritized_items'] as List? ?? [];
        if (deprioritized.isNotEmpty) {
          buffer.writeln('🚫 Avoided: ${deprioritized.join(', ')}');
        }

        _result = buffer.toString();
      } else {
        final data = jsonDecode(response.body);
        _result = '❌ HTTP ${response.statusCode}\n'
            'Error: ${data['error'] ?? data['detail'] ?? response.body}';
      }
    } catch (e) {
      _result = '❌ Error:\n$e';
    }

    if (mounted) setState(() => _loading = false);
  }

  @override
  void dispose() {
    _occasionCtrl.dispose();
    _weatherCtrl.dispose();
    _genderCtrl.dispose();
    _tempCtrl.dispose();
    _styleCtrl.dispose();
    _colorCtrl.dispose();
    _avoidCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header card
          Card(
            elevation: 2,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  const Text('👗 Outfit Recommendations', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 4),
                  const Text('POST /api/v1/outfits/recommend', style: TextStyle(color: Colors.grey, fontSize: 12)),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),

          // Form fields
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Parameters', style: TextStyle(fontWeight: FontWeight.bold)),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _occasionCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Occasion *',
                      border: OutlineInputBorder(),
                      isDense: true,
                      hintText: 'office, party, beach, sport, formal...',
                    ),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _weatherCtrl,
                          decoration: const InputDecoration(
                            labelText: 'Weather',
                            border: OutlineInputBorder(),
                            isDense: true,
                            hintText: 'rainy, sunny, cold...',
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: TextField(
                          controller: _tempCtrl,
                          decoration: const InputDecoration(
                            labelText: 'Temp (°C)',
                            border: OutlineInputBorder(),
                            isDense: true,
                          ),
                          keyboardType: TextInputType.number,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _genderCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Gender',
                      border: OutlineInputBorder(),
                      isDense: true,
                      hintText: 'male, female, non-binary...',
                    ),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _styleCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Style Preferences (comma-separated)',
                      border: OutlineInputBorder(),
                      isDense: true,
                      hintText: 'minimal, classic, streetwear...',
                    ),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _colorCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Color Preferences (comma-separated)',
                      border: OutlineInputBorder(),
                      isDense: true,
                      hintText: 'navy, charcoal, white...',
                    ),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _avoidCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Avoid Items (comma-separated)',
                      border: OutlineInputBorder(),
                      isDense: true,
                      hintText: 'shorts, tie, hat...',
                    ),
                  ),
                  const SizedBox(height: 12),
                  OutlinedButton.icon(
                    onPressed: _pickRefImage,
                    icon: const Icon(Icons.add_photo_alternate),
                    label: Text(
                      _refImage == null
                          ? 'Add Reference Image (optional)'
                          : '📷 ${_refImage!.name}',
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),

          // Submit button
          ElevatedButton.icon(
            onPressed: _loading ? null : _recommend,
            icon: const Icon(Icons.auto_awesome),
            label: const Text('Get Recommendations'),
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.all(16),
              backgroundColor: Colors.deepPurple,
              foregroundColor: Colors.white,
            ),
          ),
          const SizedBox(height: 12),

          // Results
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.grey.shade100,
              borderRadius: BorderRadius.circular(12),
            ),
            child: _loading
                ? const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator()))
                : SingleChildScrollView(child: Text(_result, style: const TextStyle(fontSize: 13, fontFamily: 'monospace'))),
          ),
        ],
      ),
    );
  }
}

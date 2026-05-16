



 Import ‘dart:convert’;
 Import ‘dart:io’;
 Import ‘package:flutter/material.dart’;
 Import ‘package:http/http.dart’ as http;
 Import ‘package:image_picker/image_picker.dart’;
 
 Void main() => runApp(const FashionpediaApp());
 
 // ═══════════════════════════════════════════════════════════════════════════
 // MAIN APP — Simple Flutter client for the Fashionpedia FastAPI service.
 //
 // This app provides 3 tabs, one for each API endpoint:
 //   Tab 1: Health Check   → GET  /api/v1/health
 //   Tab 2: Image Analysis → POST /api/v1/images/analyze
 //   Tab 3: Outfit Recommend → POST /api/v1/outfits/recommend
 // ═══════════════════════════════════════════════════════════════════════════
 
 Class FashionpediaApp extends StatelessWidget {
   Const FashionpediaApp({super.key});
 
   @override
   Widget build(BuildContext context) {
     Return MaterialApp(
       Title: ‘Fashionpedia Client’,
       debugShowCheckedModeBanner: false,
       theme: ThemeData(
         colorSchemeSeed: Colors.deepPurple,
         useMaterial3: true,
       ),
       Home: const HomePage(),
     );
   }
 }
 
 // ═══════════════════════════════════════════════════════════════════════════
 // HOME PAGE — Tab-based navigation between the 3 endpoints.
 // ═══════════════════════════════════════════════════════════════════════════
 
 Class HomePage extends StatefulWidget {
   Const HomePage({super.key});
 
   @override
   State<HomePage> createState() => _HomePageState();
 }
 
 Class _HomePageState extends State<HomePage> {
   Int _currentTab = 0;
 
   // ── CHANGE THIS to your server’s address ──────────────────────────────
   // For Android emulator use: http://10.0.2.2:8000
   // For iOS simulator or web use: http://localhost:8000
   // For real device use your machine’s local IP: http://192.168.x.x:8000
   Static const String baseUrl = ‘http://localhost:8000/api/v1’;
 
   Final List<Widget> _pages = [
     Const HealthCheckTab(baseUrl: baseUrl),
     Const ImageAnalysisTab(baseUrl: baseUrl),
     Const OutfitRecommendTab(baseUrl: baseUrl),
   ];
 
   @override
   Widget build(BuildContext context) {
     Return Scaffold(
       appBar: AppBar(
         title: const Text(‘👗 Fashionpedia API Client’),
         centerTitle: true,
       ),
       Body: _pages[_currentTab],
       bottomNavigationBar: NavigationBar(
         selectedIndex: _currentTab,
         onDestinationSelected: (i) => setState(() => _currentTab = i),
         destinations: const [
           NavigationDestination(icon: Icon(Icons.favorite), label: ‘Health’),
           NavigationDestination(icon: Icon(Icons.image), label: ‘Analyze’),
           NavigationDestination(icon: Icon(Icons.checkroom), label: ‘Recommend’),
         ],
       ),
     );
   }
 }
 
 // ═══════════════════════════════════════════════════════════════════════════
 // TAB 1: HEALTH CHECK
 // Calls: GET /api/v1/health
 // Expected response: {“status”: “healthy”, “service”: “fashionpedia-api”}
 // ═══════════════════════════════════════════════════════════════════════════
 
 Class HealthCheckTab extends StatefulWidget {
   Final String baseUrl;
   Const HealthCheckTab({super.key, required this.baseUrl});
 
   @override
   State<HealthCheckTab> createState() => _HealthCheckTabState();
 }
 
 Class _HealthCheckTabState extends State<HealthCheckTab> {
   String _result = ‘Tap the button to check service health.’;
   Bool _loading = false;
 
   Future<void> _checkHealth() async {
     setState(() {
       _loading = true;
       _result = ‘Checking...’;
     });
 
     Try {
       Final response = await http.get(
         Uri.parse(‘${widget.baseUrl}/health’),
       );
 
       If (response.statusCode == 200) {
         Final data = jsonDecode(response.body);
         _result = ‘✅ Status: ${data[‘status’]}\n’
             ‘🏷️ Service: ${data[‘service’]}’;
       } else {
         _result = ‘❌ HTTP ${response.statusCode}\n${response.body}’;
       }
     } catch (e) {
       _result = ‘❌ Connection error:\n$e’;
     }
 
     setState(() => _loading = false);
   }
 
   @override
   Widget build(BuildContext context) {
     Return Padding(
       Padding: const EdgeInsets.all(24),
       Child: Column(
         mainAxisAlignment: MainAxisAlignment.center,
         children: [
           const Icon(Icons.monitor_heart, size: 64, color: Colors.green),
           const SizedBox(height: 16),
           const Text(‘Health Check’, style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
           const SizedBox(height: 8),
           const Text(‘GET /api/v1/health’, style: TextStyle(color: Colors.grey)),
           const SizedBox(height: 24),
           ElevatedButton.icon(
             onPressed: _loading ? null : _checkHealth,
             icon: const Icon(Icons.refresh),
             label: const Text(‘Check Health’),
           ),
           Const SizedBox(height: 24),
           Container(
             Width: double.infinity,
             Padding: const EdgeInsets.all(16),
             Decoration: BoxDecoration(
               Color: Colors.grey.shade100,
               borderRadius: BorderRadius.circular(12),
             ),
             Child: _loading
                 ? const Center(child: CircularProgressIndicator())
                 : Text(_result, style: const TextStyle(fontSize: 16)),
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
 
 Class ImageAnalysisTab extends StatefulWidget {
   Final String baseUrl;
   Const ImageAnalysisTab({super.key, required this.baseUrl});
 
   @override
   State<ImageAnalysisTab> createState() => _ImageAnalysisTabState();
 }
 
 Class _ImageAnalysisTabState extends State<ImageAnalysisTab> {
   Final _occasionCtrl = TextEditingController(text: ‘office’);
   Final _weatherCtrl = TextEditingController(text: ‘sunny’);
   Final _genderCtrl = TextEditingController(text: ‘female’);
   Final _tempCtrl = TextEditingController(text: ‘22’);
 
   XFile? _pickedImage;
   String _result = ‘Pick an image and tap “Analyze”.’;
   Bool _loading = false;
 
   Future<void> _pickImage() async {
     Final picker = ImagePicker();
     Final image = await picker.pickImage(source: ImageSource.gallery);
     If (image != null) {
       setState(() {
         _pickedImage = image;
         _result = ‘Image selected: ${image.name}\nTap “Analyze” to send.’;
       });
     }
   }
 
   Future<void> _analyzeImage() async {
     If (_pickedImage == null) {
       setState(() => _result = ‘⚠️ Please pick an image first.’);
       return;
     }
 
     setState(() {
       _loading = true;
       _result = ‘🔄 Uploading and analyzing...’;
     });
 
     Try {
       // Build multipart request
       Final uri = Uri.parse(‘${widget.baseUrl}/images/analyze’);
       Final request = http.MultipartRequest(‘POST’, uri);
 
       // Attach the image file
       Request.files.add(await http.MultipartFile.fromPath(‘image’, _pickedImage!.path));
 
       // Attach optional form fields
       If (_occasionCtrl.text.isNotEmpty) request.fields[‘occasion’] = _occasionCtrl.text;
       If (_weatherCtrl.text.isNotEmpty) request.fields[‘weather’] = _weatherCtrl.text;
       If (_genderCtrl.text.isNotEmpty) request.fields[‘gender’] = _genderCtrl.text;
       If (_tempCtrl.text.isNotEmpty) request.fields[‘temperature_celsius’] = _tempCtrl.text;
 
       // Send request
       Final streamedResponse = await request.send();
       Final response = await http.Response.fromStream(streamedResponse);
 
       If (response.statusCode == 200) {
         Final data = jsonDecode(response.body);
 
         // Extract key results for display
         Final detections = data[‘fashionpedia_detections’] as List;
         Final prediction = data[‘outfit_prediction’];
         Final quality = data[‘quality_metadata’];
 
         Final buffer = StringBuffer();
         Buffer.writeln(‘✅ Analysis Complete!\n’);
         Buffer.writeln(‘📊 Style: ${prediction[‘predicted_style_label’]}’);
         Buffer.writeln(‘🎯 Occasion fit: ${prediction[‘occasion_alignment’]}’);
         Buffer.writeln(‘🌤️ Weather fit: ${prediction[‘weather_alignment’]}’);
         Buffer.writeln(‘💯 Confidence: ${(prediction[‘confidence’] * 100).toStringAsFixed(0)}%\n’);
         Buffer.writeln(‘👕 Detected ${detections.length} item(s):’);
         For (final item in detections.take(8)) {
           Buffer.writeln(‘  • ${item[‘label’]} (${(item[‘confidence’] * 100).toStringAsFixed(0)}%)’);
         }
         If (detections.length > 8) buffer.writeln(‘  ... and ${detections.length – 8} more’);
         Buffer.writeln(‘\n🎨 Dominant colors:’);
         For (final color in (quality[‘dominant_colors’] as List).take(5)) {
           Buffer.writeln(‘  • ${color[‘name’]} (${color[‘hex’]})’);
         }
         If ((quality[‘quality_warnings’] as List).isNotEmpty) {
           Buffer.writeln(‘\n⚠️ Warnings:’);
           For (final w in quality[‘quality_warnings’]) {
             Buffer.writeln(‘  • $w’);
           }
         }
 
         _result = buffer.toString();
       } else {
         Final data = jsonDecode(response.body);
         _result = ‘❌ HTTP ${response.statusCode}\n’
             ‘Error: ${data[‘error’] ?? data[‘detail’] ?? response.body}’;
       }
     } catch (e) {
       _result = ‘❌ Error:\n$e’;
     }
 
     setState(() => _loading = false);
   }
 
   @override
   Widget build(BuildContext context) {
     Return SingleChildScrollView(
       Padding: const EdgeInsets.all(16),
       Child: Column(
         crossAxisAlignment: CrossAxisAlignment.stretch,
         children: [
           // Image picker
           Card(
             Child: Padding(
               Padding: const EdgeInsets.all(16),
               Child: Column(
                 Children: [
                   Const Text(‘📸 Image Analysis’, style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                   Const SizedBox(height: 4),
                   Const Text(‘POST /api/v1/images/analyze’, style: TextStyle(color: Colors.grey, fontSize: 12)),
                   Const SizedBox(height: 16),
                   ElevatedButton.icon(
                     onPressed: _pickImage,
                     icon: const Icon(Icons.photo_library),
                     label: Text(_pickedImage == null ? ‘Pick Image’ : ‘📷 ${_pickedImage!.name}’),
                   ),
                 ],
               ),
             ),
           ),
           Const SizedBox(height: 12),
 
           // Form fields
           Card(
             Child: Padding(
               Padding: const EdgeInsets.all(16),
               Child: Column(
                 crossAxisAlignment: CrossAxisAlignment.start,
                 children: [
                   const Text(‘Context (optional)’, style: TextStyle(fontWeight: FontWeight.bold)),
                   const SizedBox(height: 12),
                   Row(children: [
                     Expanded(child: TextField(controller: _occasionCtrl, decoration: const InputDecoration(labelText: ‘Occasion’, border: OutlineInputBorder(), isDense: true))),
                     Const SizedBox(width: 8),
                     Expanded(child: TextField(controller: _weatherCtrl, decoration: const InputDecoration(labelText: ‘Weather’, border: OutlineInputBorder(), isDense: true))),
                   ]),
                   Const SizedBox(height: 8),
                   Row(children: [
                     Expanded(child: TextField(controller: _genderCtrl, decoration: const InputDecoration(labelText: ‘Gender’, border: OutlineInputBorder(), isDense: true))),
                     Const SizedBox(width: 8),
                     Expanded(child: TextField(controller: _tempCtrl, decoration: const InputDecoration(labelText: ‘Temp (°C)’, border: OutlineInputBorder(), isDense: true), keyboardType: TextInputType.number)),
                   ]),
                 ],
               ),
             ),
           ),
           Const SizedBox(height: 12),
 
           // Analyze button
           ElevatedButton.icon(
             onPressed: _loading ? null : _analyzeImage,
             icon: const Icon(Icons.search),
             label: const Text(‘Analyze Image’),
             style: ElevatedButton.styleFrom(padding: const EdgeInsets.all(16)),
           ),
           Const SizedBox(height: 12),
 
           // Results
           Container(
             Padding: const EdgeInsets.all(16),
             Decoration: BoxDecoration(color: Colors.grey.shade100, borderRadius: BorderRadius.circular(12)),
             Child: _loading
                 ? const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator()))
                 : Text(_result, style: const TextStyle(fontSize: 14)),
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
 
 Class OutfitRecommendTab extends StatefulWidget {
   Final String baseUrl;
   Const OutfitRecommendTab({super.key, required this.baseUrl});
 
   @override
   State<OutfitRecommendTab> createState() => _OutfitRecommendTabState();
 }
 
 Class _OutfitRecommendTabState extends State<OutfitRecommendTab> {
   Final _occasionCtrl = TextEditingController(text: ‘office’);
   Final _weatherCtrl = TextEditingController(text: ‘rainy’);
   Final _genderCtrl = TextEditingController(text: ‘male’);
   Final _tempCtrl = TextEditingController(text: ‘16’);
   Final _styleCtrl = TextEditingController(text: ‘minimal, classic’);
   Final _colorCtrl = TextEditingController(text: ‘navy, charcoal’);
   Final _avoidCtrl = TextEditingController(text: ‘shorts’);
 
   XFile? _refImage;
   String _result = ‘Fill in the occasion and tap “Get Recommendations”.’;
   Bool _loading = false;
 
   Future<void> _pickRefImage() async {
     Final picker = ImagePicker();
     Final image = await picker.pickImage(source: ImageSource.gallery);
     If (image != null) setState(() => _refImage = image);
   }
 
   Future<void> _recommend() async {
     If (_occasionCtrl.text.isEmpty) {
       setState(() => _result = ‘⚠️ Occasion is required.’);
       return;
     }
 
     setState(() {
       _loading = true;
       _result = ‘🔄 Generating recommendations...’;
     });
 
     Try {
       Final uri = Uri.parse(‘${widget.baseUrl}/outfits/recommend’);
       Final request = http.MultipartRequest(‘POST’, uri);
 
       // Required field
       Request.fields[‘occasion’] = _occasionCtrl.text;
 
       // Optional fields
       If (_weatherCtrl.text.isNotEmpty) request.fields[‘weather’] = _weatherCtrl.text;
       If (_genderCtrl.text.isNotEmpty) request.fields[‘gender’] = _genderCtrl.text;
       If (_tempCtrl.text.isNotEmpty) request.fields[‘temperature_celsius’] = _tempCtrl.text;
       If (_styleCtrl.text.isNotEmpty) request.fields[‘style_preferences’] = _styleCtrl.text;
       If (_colorCtrl.text.isNotEmpty) request.fields[‘color_preferences’] = _colorCtrl.text;
       If (_avoidCtrl.text.isNotEmpty) request.fields[‘avoid_items’] = _avoidCtrl.text;
 
       // Optional reference image
       If (_refImage != null) {
         Request.files.add(await http.MultipartFile.fromPath(‘image’, _refImage!.path));
       }
 
       Final streamedResponse = await request.send();
       Final response = await http.Response.fromStream(streamedResponse);
 
       If (response.statusCode == 200) {
         Final data = jsonDecode(response.body);
         Final recommendations = data[‘recommendations’] as List;
 
         Final buffer = StringBuffer();
         Buffer.writeln(‘✅ ${recommendations.length} Outfit(s) Recommended!\n’);
 
         For (final rec in recommendations) {
           Buffer.writeln(‘━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━’);
           Buffer.writeln(‘#${rec[‘rank’]} ${rec[‘title’]}’);
           Buffer.writeln(‘   Style: ${rec[‘style_label’]}’);
           Buffer.writeln(‘   Confidence: ${(rec[‘confidence’] * 100).toStringAsFixed(0)}%’);
           Buffer.writeln(‘   👕 Items: ${(rec[‘primary_items’] as List).join(‘, ‘)}’);
           Buffer.writeln(‘   👜 Extras: ${(rec[‘optional_items’] as List).join(‘, ‘)}’);
           Buffer.writeln(‘   🎨 Colors: ${(rec[‘palette_direction’] as List).join(‘, ‘)}’);
           Buffer.writeln(‘   💡 Why: ${(rec[‘reasoning’] as List).first}’);
           Buffer.writeln(‘’);
         }
 
         If ((data[‘deprioritized_items’] as List).isNotEmpty) {
           Buffer.writeln(‘🚫 Avoided: ${(data[‘deprioritized_items’] as List).join(‘, ‘)}’);
         }
 
         _result = buffer.toString();
       } else {
         Final data = jsonDecode(response.body);
         _result = ‘❌ HTTP ${response.statusCode}\n’
             ‘Error: ${data[‘error’] ?? data[‘detail’] ?? response.body}’;
       }
     } catch (e) {
       _result = ‘❌ Error:\n$e’;
     }
 
     setState(() => _loading = false);
   }
 
   @override
   Widget build(BuildContext context) {
     Return SingleChildScrollView(
       Padding: const EdgeInsets.all(16),
       Child: Column(
         crossAxisAlignment: CrossAxisAlignment.stretch,
         children: [
           Card(
             Child: Padding(
               Padding: const EdgeInsets.all(16),
               Child: Column(
                 Children: [
                   Const Text(‘👗 Outfit Recommendations’, style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                   Const SizedBox(height: 4),
                   Const Text(‘POST /api/v1/outfits/recommend’, style: TextStyle(color: Colors.grey, fontSize: 12)),
                 ],
               ),
             ),
           ),
           Const SizedBox(height: 12),
 
           // Form fields
           Card(
             Child: Padding(
               Padding: const EdgeInsets.all(16),
               Child: Column(
                 crossAxisAlignment: CrossAxisAlignment.start,
                 children: [
                   const Text(‘Parameters’, style: TextStyle(fontWeight: FontWeight.bold)),
                   const SizedBox(height: 12),
                   TextField(controller: _occasionCtrl, decoration: const InputDecoration(labelText: ‘Occasion *’, border: OutlineInputBorder(), isDense: true, hintText: ‘office, party, beach, sport...’)),
                   Const SizedBox(height: 8),
                   Row(children: [
                     Expanded(child: TextField(controller: _weatherCtrl, decoration: const InputDecoration(labelText: ‘Weather’, border: OutlineInputBorder(), isDense: true))),
                     Const SizedBox(width: 8),
                     Expanded(child: TextField(controller: _tempCtrl, decoration: const InputDecoration(labelText: ‘Temp (°C)’, border: OutlineInputBorder(), isDense: true), keyboardType: TextInputType.number)),
                   ]),
                   Const SizedBox(height: 8),
                   TextField(controller: _genderCtrl, decoration: const InputDecoration(labelText: ‘Gender’, border: OutlineInputBorder(), isDense: true)),
                   Const SizedBox(height: 8),
                   TextField(controller: _styleCtrl, decoration: const InputDecoration(labelText: ‘Style Preferences (comma-





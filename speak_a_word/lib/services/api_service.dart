import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  // Unsplash Image Search
  static Future<String?> searchUnsplashImage(String query, String apiKey) async {
    if (apiKey.isEmpty) throw Exception('Unsplash API Key is empty');

    final url = Uri.parse('https://api.unsplash.com/search/photos?query=$query&per_page=1&client_id=$apiKey');
    
    try {
      final response = await http.get(url);
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['results'] != null && data['results'].isNotEmpty) {
          // Return the regular sized image URL
          return data['results'][0]['urls']['regular'];
        }
      }
      return null;
    } catch (e) {
      throw Exception('Failed to fetch image from Unsplash: $e');
    }
  }
}

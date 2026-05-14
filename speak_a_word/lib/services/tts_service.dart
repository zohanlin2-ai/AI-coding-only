import 'package:flutter_tts/flutter_tts.dart';

class TTSService {
  final FlutterTts _flutterTts = FlutterTts();

  Future<void> init() async {
    await _flutterTts.setVolume(1.0);
    await _flutterTts.setSpeechRate(0.5); // Slightly slower, suitable for infants
    await _flutterTts.setPitch(1.0);
  }

  Future<void> speak(String text, String languageCode) async {
    // languageCode: 'en-US', 'ja-JP', 'zh-TW'
    await _flutterTts.setLanguage(languageCode);
    await _flutterTts.speak(text);
  }
  
  Future<void> stop() async {
    await _flutterTts.stop();
  }
}

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AppSettings {
  final String unsplashApiKey;

  AppSettings({
    this.unsplashApiKey = '',
  });

  AppSettings copyWith({
    String? unsplashApiKey,
  }) {
    return AppSettings(
      unsplashApiKey: unsplashApiKey ?? this.unsplashApiKey,
    );
  }
}

class SettingsNotifier extends Notifier<AppSettings> {
  @override
  AppSettings build() {
    _loadSettings();
    return AppSettings();
  }

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    state = AppSettings(
      unsplashApiKey: prefs.getString('unsplashApiKey') ?? '',
    );
  }

  Future<void> setUnsplashApiKey(String key) async {
    state = state.copyWith(unsplashApiKey: key);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('unsplashApiKey', key);
  }
}

final settingsProvider = NotifierProvider<SettingsNotifier, AppSettings>(() {
  return SettingsNotifier();
});

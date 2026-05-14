import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../viewmodels/settings_viewmodel.dart';
import 'package:url_launcher/url_launcher.dart'; // To open external links in the browser

class SettingsView extends ConsumerWidget {
  const SettingsView({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(settingsProvider);
    final notifier = ref.read(settingsProvider.notifier);

    return Scaffold(
      appBar: AppBar(
        title: const Text('設定'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16.0),
        children: [
          const Text('Unsplash API Key (用於免費圖庫)', style: TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          TextField(
            controller: TextEditingController(text: settings.unsplashApiKey)..selection = TextSelection.collapsed(offset: settings.unsplashApiKey.length),
            decoration: const InputDecoration(
              border: OutlineInputBorder(),
              hintText: '輸入您的 Unsplash Access Key',
            ),
            onChanged: (value) => notifier.setUnsplashApiKey(value),
          ),
          const SizedBox(height: 24),
          const Divider(),
          const SizedBox(height: 16),
          const Text(
            '關於圖片來源：',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          const Text(
            '本 App 目前主要採用 Unsplash 免費圖庫作為圖片來源。考量到目前市面上尚無穩定且完全免費的 AI 生成圖片 API 服務，為了確保教學品質與系統穩定性，暫不開放 AI 生成功能。',
            style: TextStyle(color: Colors.grey),
          ),
        ],
      ),
    );
  }
}

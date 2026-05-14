import 'package:flutter/material.dart';
import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';
import '../viewmodels/settings_viewmodel.dart';
import '../services/api_service.dart';
import '../services/db_service.dart';
import '../models/word_item.dart';

class AddPrepView extends ConsumerStatefulWidget {
  const AddPrepView({super.key});

  @override
  ConsumerState<AddPrepView> createState() => _AddPrepViewState();
}

class _AddPrepViewState extends ConsumerState<AddPrepView> {
  final TextEditingController _wordController = TextEditingController();
  String _selectedLanguage = 'zh-TW';
  String? _previewImageUrl; // URL of the fetched/generated image

  Widget _buildImage(String path) {
    if (path.startsWith('base64,')) {
      return Image.memory(
        base64Decode(path.substring(7)),
        fit: BoxFit.cover,
        errorBuilder: (c, e, s) => const Center(child: Icon(Icons.error, color: Colors.red)),
      );
    } else {
      return Image.network(
        path,
        fit: BoxFit.cover,
        errorBuilder: (c, e, s) => const Center(child: Icon(Icons.error, color: Colors.red)),
      );
    }
  }

  String _detectLanguage(String text) {
    if (text.isEmpty) return _selectedLanguage;

    // 1. Check for Japanese characters (Hiragana, Katakana, or Japanese-specific Kanji)
    // Included common Japanese Kanji variants like 転, 込, 枠, 峠, etc.
    if (RegExp(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]').hasMatch(text)) {
      // If it contains Hiragana/Katakana, it's definitely Japanese
      if (RegExp(r'[\u3040-\u309F\u30A0-\u30FF]').hasMatch(text)) {
        return 'ja-JP';
      }
      
      // If it's pure Kanji, check for Japanese-specific Kanji variants
      // This is a heuristic list of Kanji that are common in Japanese but not in Traditional Chinese
      if (RegExp(r'[転込枠峠匂畑腺雫込喫]').hasMatch(text)) {
        return 'ja-JP';
      }
    }

    // 2. Check for Chinese characters
    if (RegExp(r'[\u4E00-\u9FFF]').hasMatch(text)) {
      return 'zh-TW';
    }
    // Check for English characters
    if (RegExp(r'[a-zA-Z]').hasMatch(text)) {
      return 'en-US';
    }
    return _selectedLanguage;
  }

  String _getLanguageLabel(String code) {
    switch (code) {
      case 'zh-TW': return '中文';
      case 'en-US': return '英文';
      case 'ja-JP': return '日文';
      default: return '未知';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('新增備課單字'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: _wordController,
              onChanged: (value) {
                final detected = _detectLanguage(value);
                if (detected != _selectedLanguage) {
                  setState(() {
                    _selectedLanguage = detected;
                  });
                }
              },
              decoration: const InputDecoration(
                labelText: '輸入單字 (例如: 蘋果)',
                border: OutlineInputBorder(),
              ),
              style: const TextStyle(fontSize: 24),
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                const Text('發音語言：', style: TextStyle(color: Colors.grey, fontSize: 12)),
                ActionChip(
                  label: Text(_getLanguageLabel(_selectedLanguage)),
                  onPressed: () {
                    setState(() {
                      // Cycle through languages
                      if (_selectedLanguage == 'zh-TW') _selectedLanguage = 'en-US';
                      else if (_selectedLanguage == 'en-US') _selectedLanguage = 'ja-JP';
                      else _selectedLanguage = 'zh-TW';
                    });
                  },
                  avatar: const Icon(Icons.translate, size: 16),
                  padding: EdgeInsets.zero,
                ),
              ],
            ),
            const SizedBox(height: 16),
            Center(
              child: ElevatedButton.icon(
                onPressed: () async {
                  if (_wordController.text.isEmpty) return;
                  final settings = ref.read(settingsProvider);
                  if (settings.unsplashApiKey.isEmpty) {
                    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('請先在設定頁面輸入 Unsplash API Key')));
                    return;
                  }
                  try {
                    final url = await ApiService.searchUnsplashImage(_wordController.text, settings.unsplashApiKey);
                    if (url != null) {
                      setState(() { _previewImageUrl = url; });
                    } else {
                      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('找不到相關圖片')));
                    }
                  } catch (e) {
                    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
                  }
                },
                icon: const Icon(Icons.image_search),
                label: const Text('搜尋圖庫圖片'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
                  backgroundColor: Colors.blue[100],
                ),
              ),
            ),
            const SizedBox(height: 24),
            // Image Preview Area
            Container(
              height: 250,
              decoration: BoxDecoration(
                border: Border.all(color: Colors.grey),
                borderRadius: BorderRadius.circular(8),
              ),
              alignment: Alignment.center,
              child: _previewImageUrl == null
                  ? const Text('尚未選擇圖片', style: TextStyle(color: Colors.grey))
                  : _buildImage(_previewImageUrl!),
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: _previewImageUrl == null
                  ? null
                  : () async {
                      final newItem = WordItem(
                        id: const Uuid().v4(),
                        word: _wordController.text,
                        language: _selectedLanguage,
                        imagePath: _previewImageUrl!,
                      );
                      await DatabaseService.instance.insertWord(newItem);
                      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('儲存成功！')));
                      Navigator.pop(context);
                    },
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
                textStyle: const TextStyle(fontSize: 20),
                backgroundColor: Colors.teal,
                foregroundColor: Colors.white,
              ),
              child: const Text('儲存此單字'),
            ),
          ],
        ),
      ),
    );
  }
}

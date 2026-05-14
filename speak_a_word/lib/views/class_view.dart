import 'package:flutter/material.dart';
import 'dart:convert';
import '../services/db_service.dart';
import '../services/tts_service.dart';
import '../models/word_item.dart';

class ClassView extends StatefulWidget {
  final List<WordItem>? selectedWords;
  const ClassView({super.key, this.selectedWords});

  @override
  State<ClassView> createState() => _ClassViewState();
}

class _ClassViewState extends State<ClassView> {
  final PageController _pageController = PageController();
  final TTSService _ttsService = TTSService();
  List<WordItem> _words = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _initClass();
  }

  Future<void> _initClass() async {
    await _ttsService.init();
    await _loadWords();
    if (_words.isNotEmpty) {
      _speakCurrentWord(0);
    }
  }

  Future<void> _loadWords() async {
    setState(() => _isLoading = true);
    if (widget.selectedWords != null && widget.selectedWords!.isNotEmpty) {
      _words = List.from(widget.selectedWords!);
    } else {
      _words = await DatabaseService.instance.fetchActiveWords();
    }
    setState(() => _isLoading = false);
  }

  Future<void> _speakCurrentWord(int index) async {
    if (index >= 0 && index < _words.length) {
      final word = _words[index];
      await _ttsService.speak(word.word, word.language);
    }
  }

  void _onPageChanged(int index) {
    _speakCurrentWord(index);
  }

  @override
  void dispose() {
    _pageController.dispose();
    _ttsService.stop();
    super.dispose();
  }

  Widget _buildImage(String path) {
    if (path.startsWith('base64,')) {
      return Image.memory(
        base64Decode(path.substring(7)),
        fit: BoxFit.cover,
        errorBuilder: (c, e, s) => const Center(child: Icon(Icons.error, color: Colors.white, size: 50)),
      );
    } else {
      return Image.network(
        path,
        fit: BoxFit.cover,
        errorBuilder: (c, e, s) => const Center(child: Icon(Icons.error, color: Colors.white, size: 50)),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    if (_words.isEmpty) {
      return Scaffold(
        appBar: AppBar(title: const Text('開始上課')),
        body: const Center(child: Text('還沒有需要練習的單字喔！', style: TextStyle(fontSize: 18))),
      );
    }

    return Scaffold(
      backgroundColor: Colors.black87,
      appBar: AppBar(
        title: const Text('上課囉！'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        foregroundColor: Colors.white,
      ),
      body: PageView.builder(
        controller: _pageController,
        onPageChanged: _onPageChanged,
        itemCount: _words.length,
        itemBuilder: (context, index) {
          final word = _words[index];
          return Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Expanded(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(20),
                    child: _buildImage(word.imagePath),
                  ),
                ),
                const SizedBox(height: 30),
                Text(
                  word.word,
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 64, fontWeight: FontWeight.bold, color: Colors.white),
                ),
                const SizedBox(height: 20),
                IconButton(
                  iconSize: 64,
                  color: Colors.yellowAccent,
                  icon: const Icon(Icons.volume_up),
                  onPressed: () => _speakCurrentWord(index),
                ),
                const SizedBox(height: 40),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    ElevatedButton.icon(
                      onPressed: () async {
                        await DatabaseService.instance.updateExposure(word.id, word.exposureCount + 5, isLearned: true);
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(content: Text('太棒了！已將「${word.word}」移至已學會清單'), duration: const Duration(seconds: 1)),
                        );
                        _loadWords();
                      },
                      icon: const Icon(Icons.check_circle),
                      label: const Text('寶寶學會了'),
                      style: ElevatedButton.styleFrom(backgroundColor: Colors.green, foregroundColor: Colors.white),
                    ),
                    const SizedBox(width: 20),
                    ElevatedButton.icon(
                      onPressed: () async {
                        await DatabaseService.instance.updateExposure(word.id, word.exposureCount + 1, isLearned: false);
                        if (_pageController.page!.toInt() < _words.length - 1) {
                          _pageController.nextPage(duration: const Duration(milliseconds: 300), curve: Curves.easeInOut);
                        } else {
                          // 循環播放：回到第一張
                          _pageController.animateToPage(0, duration: const Duration(milliseconds: 500), curve: Curves.easeInOut);
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('已回到第一張，繼續加油！'), duration: Duration(seconds: 1)),
                          );
                        }
                      },
                      icon: const Icon(Icons.arrow_forward),
                      label: const Text('下一個'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.orange, 
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),
              ],
            ),
          );
        },
      ),
    );
  }
}

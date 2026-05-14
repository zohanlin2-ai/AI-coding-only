import 'package:flutter/material.dart';
import 'dart:convert';
import 'add_prep_view.dart';
import 'class_view.dart';
import '../services/db_service.dart';
import '../models/word_item.dart';

class PrepListView extends StatefulWidget {
  const PrepListView({super.key});

  @override
  State<PrepListView> createState() => _PrepListViewState();
}

class _PrepListViewState extends State<PrepListView> {
  late Future<List<WordItem>> _wordsFuture;

  @override
  void initState() {
    super.initState();
    _loadWords();
  }

  void _loadWords() {
    setState(() {
      _wordsFuture = DatabaseService.instance.fetchAllWords();
    });
  }

  Widget _buildImage(String path) {
    if (path.startsWith('base64,')) {
      return Image.memory(
        base64Decode(path.substring(7)),
        width: 50,
        height: 50,
        fit: BoxFit.cover,
        errorBuilder: (c, e, s) => const Icon(Icons.image_not_supported),
      );
    } else {
      return Image.network(
        path,
        width: 50,
        height: 50,
        fit: BoxFit.cover,
        errorBuilder: (c, e, s) => const Icon(Icons.image_not_supported),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('備課管理'),
        actions: [
          PopupMenuButton<String>(
            onSelected: (value) async {
              if (value == 'reset_all') {
                await DatabaseService.instance.resetAllWords();
                _loadWords();
                ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('已重置所有單字學習狀態')));
              } else if (value == 'delete_all') {
                final confirm = await showDialog<bool>(
                  context: context,
                  builder: (ctx) => AlertDialog(
                    title: const Text('全部刪除'),
                    content: const Text('確定要刪除所有備課單字嗎？此動作無法復原。'),
                    actions: [
                      TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('取消')),
                      TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('確定刪除', style: TextStyle(color: Colors.red))),
                    ],
                  ),
                );
                if (confirm == true) {
                  await DatabaseService.instance.deleteAllWords();
                  _loadWords();
                }
              }
            },
            itemBuilder: (ctx) => [
              const PopupMenuItem(value: 'reset_all', child: Text('全部重新學習')),
              const PopupMenuItem(value: 'delete_all', child: Text('全部刪除', style: TextStyle(color: Colors.red))),
            ],
          ),
        ],
      ),
      body: FutureBuilder<List<WordItem>>(
        future: _wordsFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text('發生錯誤: ${snapshot.error}'));
          }
          final words = snapshot.data ?? [];
          if (words.isEmpty) {
            return const Center(child: Text('目前還沒有備課單字，請點擊右下角新增！'));
          }
          return ListView.builder(
            itemCount: words.length,
            itemBuilder: (context, index) {
              final word = words[index];

              return ListTile(
                leading: Checkbox(
                  value: word.isSelected,
                  onChanged: (val) async {
                    await DatabaseService.instance.updateSelection(word.id, val ?? false);
                    _loadWords();
                  },
                ),
                title: Row(
                  children: [
                    _buildImage(word.imagePath),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(word.word, style: const TextStyle(fontSize: 20)),
                        ],
                      ),
                    ),
                    if (word.isLearned)
                      Container(
                        margin: const EdgeInsets.only(left: 8),
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(color: Colors.green, borderRadius: BorderRadius.circular(4)),
                        child: const Text('已學會', style: TextStyle(color: Colors.white, fontSize: 10)),
                      ),
                  ],
                ),
                subtitle: null, // Moved to title column for better layout
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    IconButton(
                      icon: const Icon(Icons.refresh, color: Colors.orange),
                      tooltip: '重新學習',
                      onPressed: () async {
                        await DatabaseService.instance.updateExposure(word.id, 0, isLearned: false);
                        _loadWords();
                        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('已重置「${word.word}」')));
                      },
                    ),
                    IconButton(
                      icon: const Icon(Icons.delete_outline, color: Colors.red),
                      tooltip: '刪除',
                      onPressed: () async {
                        final confirm = await showDialog<bool>(
                          context: context,
                          builder: (ctx) => AlertDialog(
                            title: const Text('刪除單字'),
                            content: Text('確定要刪除「${word.word}」嗎？'),
                            actions: [
                              TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('取消')),
                              TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('刪除', style: TextStyle(color: Colors.red))),
                            ],
                          ),
                        );
                        if (confirm == true) {
                          await DatabaseService.instance.deleteWord(word.id);
                          _loadWords();
                        }
                      },
                    ),
                  ],
                ),
              );
            },
          );
        },
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () async {
          await Navigator.push(
            context,
            MaterialPageRoute(builder: (context) => const AddPrepView()),
          );
          _loadWords();
        },
        icon: const Icon(Icons.add),
        label: const Text('新增單字'),
      ),
    );
  }
}

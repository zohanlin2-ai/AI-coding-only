import 'package:sqflite/sqflite.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:path/path.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'dart:io' show Platform;
import '../models/word_item.dart';

class DatabaseService {
  static final DatabaseService instance = DatabaseService._init();
  static Database? _database;
  
  // In-memory mock DB for Web testing
  final Map<String, WordItem> _webDb = {};

  DatabaseService._init();

  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDB('speak_a_word.db');
    return _database!;
  }

  Future<Database> _initDB(String filePath) async {
    // Windows/Linux need sqflite_common_ffi to run SQLite
    if (!kIsWeb && (Platform.isWindows || Platform.isLinux)) {
      sqfliteFfiInit();
      databaseFactory = databaseFactoryFfi;
    }
    
    final dbPath = await getDatabasesPath();
    final path = join(dbPath, filePath);

    return await openDatabase(path, version: 1, onCreate: _createDB);
  }

  Future _createDB(Database db, int version) async {
    const idType = 'TEXT PRIMARY KEY';
    const textType = 'TEXT NOT NULL';
    const integerType = 'INTEGER NOT NULL';

    await db.execute('''
CREATE TABLE words (
  id $idType,
  word $textType,
  language $textType,
  imagePath $textType,
  exposureCount $integerType,
  isLearned $integerType DEFAULT 0,
  isSelected $integerType DEFAULT 1
)
''');
  }

  Future<void> insertWord(WordItem wordItem) async {
    if (kIsWeb) {
      _webDb[wordItem.id] = wordItem;
      return;
    }

    final db = await instance.database;
    await db.insert(
      'words',
      wordItem.toMap(),
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<List<WordItem>> fetchAllWords() async {
    if (kIsWeb) {
      return _webDb.values.toList()..sort((a, b) => a.exposureCount.compareTo(b.exposureCount));
    }

    final db = await instance.database;
    final result = await db.query('words', orderBy: 'exposureCount ASC');

    return result.map((json) => WordItem.fromMap(json)).toList();
  }

  Future<List<WordItem>> fetchActiveWords() async {
    if (kIsWeb) {
      return _webDb.values.where((w) => !w.isLearned && w.isSelected).toList()..sort((a, b) => a.exposureCount.compareTo(b.exposureCount));
    }
    final db = await instance.database;
    final result = await db.query('words', where: 'isLearned = 0 AND isSelected = 1', orderBy: 'exposureCount ASC');
    return result.map((json) => WordItem.fromMap(json)).toList();
  }

  Future<void> updateSelection(String id, bool isSelected) async {
    if (kIsWeb) {
      final old = _webDb[id];
      if (old != null) {
        _webDb[id] = WordItem(
          id: old.id,
          word: old.word,
          language: old.language,
          imagePath: old.imagePath,
          exposureCount: old.exposureCount,
          isLearned: old.isLearned,
          isSelected: isSelected,
        );
      }
      return;
    }
    final db = await instance.database;
    await db.update('words', {'isSelected': isSelected ? 1 : 0}, where: 'id = ?', whereArgs: [id]);
  }

  Future<void> updateExposure(String id, int newCount, {bool isLearned = false}) async {
    if (kIsWeb) {
      final old = _webDb[id];
      if (old != null) {
        _webDb[id] = WordItem(
          id: old.id,
          word: old.word,
          language: old.language,
          imagePath: old.imagePath,
          exposureCount: newCount,
          isLearned: isLearned,
          isSelected: old.isSelected,
        );
      }
      return;
    }

    final db = await instance.database;
    await db.update(
      'words',
      {
        'exposureCount': newCount,
        'isLearned': isLearned ? 1 : 0,
      },
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  Future<void> deleteWord(String id) async {
    if (kIsWeb) {
      _webDb.remove(id);
      return;
    }
    final db = await instance.database;
    await db.delete('words', where: 'id = ?', whereArgs: [id]);
  }

  Future<void> deleteAllWords() async {
    if (kIsWeb) {
      _webDb.clear();
      return;
    }
    final db = await instance.database;
    await db.delete('words');
  }

  Future<void> resetAllWords() async {
    if (kIsWeb) {
      for (var id in _webDb.keys) {
        final w = _webDb[id]!;
        _webDb[id] = WordItem(
          id: w.id,
          word: w.word,
          language: w.language,
          imagePath: w.imagePath,
          exposureCount: 0,
          isLearned: false,
        );
      }
      return;
    }
    final db = await instance.database;
    await db.update('words', {'exposureCount': 0, 'isLearned': 0});
  }

  Future<void> close() async {
    if (kIsWeb) return;
    final db = await instance.database;
    db.close();
  }
}

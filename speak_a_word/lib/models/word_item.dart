class WordItem {
  final String id;
  final String word; // 想要教的字或詞 (如: 蘋果)
  final String language; // 語言 (如: zh-TW, en-US, ja-JP)
  final String imagePath; // 儲存的圖片路徑 (本地路徑)
  final int exposureCount; // 曝光次數 (供記憶學習演算法參考)
  final bool isLearned;
  final bool isSelected;

  WordItem({
    required this.id,
    required this.word,
    required this.language,
    required this.imagePath,
    this.exposureCount = 0,
    this.isLearned = false,
    this.isSelected = true,
  });

  // Convert to Map for SQLite
  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'word': word,
      'language': language,
      'imagePath': imagePath,
      'exposureCount': exposureCount,
      'isLearned': isLearned ? 1 : 0,
      'isSelected': isSelected ? 1 : 0,
    };
  }

  // Create from Map from SQLite
  factory WordItem.fromMap(Map<String, dynamic> map) {
    return WordItem(
      id: map['id'],
      word: map['word'],
      language: map['language'],
      imagePath: map['imagePath'],
      exposureCount: map['exposureCount'] ?? 0,
      isLearned: (map['isLearned'] ?? 0) == 1,
      isSelected: (map['isSelected'] ?? 1) == 1,
    );
  }
}

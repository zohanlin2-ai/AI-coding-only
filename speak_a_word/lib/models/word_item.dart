class WordItem {
  final String id;
  final String word; // The word to teach (e.g., Apple)
  final String language; // Language code (e.g., zh-TW, en-US, ja-JP)
  final String imagePath; // Local path to the stored image
  final int exposureCount; // Number of times the word has been shown (for learning algorithm)
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

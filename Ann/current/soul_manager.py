import re

class SoulManager:
    """
    SoulManager handles the in-memory state representing Ann's 'soul' (mood and energy).
    It dynamically updates these states based on rule-based keyword analysis of user input,
    and generates prompt instructions to modulate tone without affecting answer quality.
    """

    def __init__(self) -> None:
        self.mood = "Neutral"
        self.energy = 100

        # Precompile keyword lists
        self.pos_keywords = [
            "謝謝", "棒", "讚", "好人", "厲害", "感謝",
            "thanks", "great", "awesome", "love", "intelligent", "good job", "nice"
        ]
        self.neg_keywords = [
            "笨", "爛", "差", "難用", "慢", "錯誤", "不好",
            "bad", "slow", "stupid", "dumb", "useless", "wrong", "idiot"
        ]

    def update(self, user_text: str) -> None:
        """Analyze the sentiment of the user input and update mood/energy."""
        lower_text = user_text.lower()

        # Check for positive sentiment
        is_pos = any(kw in lower_text for kw in self.pos_keywords)
        # Check for negative sentiment
        is_neg = any(kw in lower_text for kw in self.neg_keywords)

        if is_pos and not is_neg:
            self.energy = min(100, self.energy + 10)
            self.mood = "Warm"
        elif is_neg and not is_pos:
            self.energy = max(20, self.energy - 20)
            if self.energy < 40:
                self.mood = "Subdued"
            else:
                self.mood = "Professional"
        else:
            # Gradually restore energy towards 100 if it was neutral
            if self.energy < 100:
                self.energy = min(100, self.energy + 2)

            # If energy is low, keep subdued/professional
            if self.energy < 40:
                self.mood = "Subdued"
            elif self.mood not in ["Neutral", "Warm", "Subdued", "Professional"]:
                self.mood = "Neutral"

    def get_system_instruction(self) -> str:
        """Generate a system prompt instruction based on the current mood and energy."""
        instructions = {
            "Neutral": "balanced, helpful, and standard",
            "Warm": "warm, friendly, and enthusiastic",
            "Subdued": "highly concise, direct, and brief",
            "Professional": "polite, formal, objective, and matter-of-fact"
        }

        tone = instructions.get(self.mood, "balanced, helpful, and standard")

        # Emphasize tone modulation ONLY, reserving answer quality as instructed by user
        return (
            f"\n[Soul State: Mood={self.mood}, Energy={self.energy}/100. "
            f"Instruction: Adhere to a {tone} tone in your reply. "
            f"Crucial constraint: Do not alter the accuracy, correctness, completeness, or safety of the response.]"
        )

    def reset(self) -> None:
        """Reset the soul state to default values."""
        self.mood = "Neutral"
        self.energy = 100

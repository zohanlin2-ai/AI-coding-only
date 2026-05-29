import logging

logger = logging.getLogger(__name__)

SUMMARIZE_PROMPT = (
    "You are a news summarizer. Summarize the following article in Traditional Chinese.\n"
    "Be concise: 3–5 sentences. Focus on the key facts. Do not editorialize.\n\n"
    "Article title: {title}\n"
    "Article content:\n"
    "{full_article_text}"
)


class NewsSummarizer:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model

    def summarize(self, title: str, text: str) -> str:
        """
        Sends the article to Ollama with the summarization prompt and returns the summary.
        Truncates the input article content if it exceeds ~10,000 characters (~3000 tokens).
        """
        max_chars = 10000
        truncated = False
        
        if len(text) > max_chars:
            text = text[:max_chars]
            truncated = True
            logger.info("Truncated article text for summarization (exceeded %d chars)", max_chars)

        full_article_text = text
        if truncated:
            full_article_text += "\n\n[注意：文章內容過長，已截斷後半部]"

        prompt = SUMMARIZE_PROMPT.format(title=title, full_article_text=full_article_text)

        messages = [
            {"role": "user", "content": prompt}
        ]

        try:
            from ollama_client import OllamaClient
            client = OllamaClient(self.base_url)
            reply = client.chat(self.model, messages)
            return reply.strip()
        except Exception as e:
            logger.error("Failed to generate summary with Ollama: %s", e)
            raise e

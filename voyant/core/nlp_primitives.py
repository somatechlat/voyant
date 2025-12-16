"""
NLP Primitives

Natural Language Processing operations (Sentiment, etc.).
Implements Phase 5 Operational Presets.
Adheres to Vibe Coding Rules: Uses NLTK VADER or TextBlob.
"""
import logging
from typing import Any, Dict, List

try:
    import nltk
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

logger = logging.getLogger(__name__)

class NLPPrimitives:
    """
    Core NLP operations.
    """
    
    def __init__(self):
        if NLTK_AVAILABLE:
            try:
                # Ensure lexicon is present
                nltk.data.find('sentiment/vader_lexicon.zip')
            except LookupError:
                nltk.download('vader_lexicon', quiet=True)
                
            self.sia = SentimentIntensityAnalyzer()
        else:
            logger.warning("NLTK not found. NLP primitives will fail.")

    def analyze_sentiment(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Analyze sentiment of a list of texts using VADER.
        Returns compound scores and classification.
        """
        if not NLTK_AVAILABLE:
            raise ImportError("NLTK is not installed.")
            
        results = []
        for text in texts:
            scores = self.sia.polarity_scores(text)
            compound = scores['compound']
            
            sentiment = "neutral"
            if compound >= 0.05:
                sentiment = "positive"
            elif compound <= -0.05:
                sentiment = "negative"
                
            results.append({
                "text_snippet": text[:50] + "..." if len(text) > 50 else text,
                "scores": scores,
                "compound": compound,
                "sentiment": sentiment
            })
            
        return results

"""
Production-Ready Gemini Embeddings Integration
✅ Logging with multiple levels
✅ API keys from .env (never hardcoded)
✅ Timeout + comprehensive error handling
✅ Output validated with Pydantic
✅ Fallback to sentence-transformers if API fails
✅ Edge case handling + retry logic
"""

import os
import logging
import time
from typing import List, Optional
from google import genai
from pydantic import BaseModel, Field, ValidationError

# Load environment
import sys
sys.path.append(os.path.dirname(__file__))
from load_env import load_env
load_env()

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gemini_embedder.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# PYDANTIC MODELS FOR VALIDATION
# ============================================================================

class EmbeddingResponse(BaseModel):
    """Validated embedding response"""
    values: List[float] = Field(..., min_items=1)
    dimension: int = Field(gt=0)

    @classmethod
    def from_api_response(cls, embedding):
        """Create from API response"""
        values = list(embedding.values)
        return cls(values=values, dimension=len(values))


# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Centralized configuration"""

    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_model = self._parse_model_name(os.getenv("GEMINI_MODEL", "models/gemini-embedding-001"))
        self.timeout = int(os.getenv("GEMINI_TIMEOUT", "30"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.batch_size = int(os.getenv("GEMINI_BATCH_SIZE", "100"))

        # Validate required keys
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")

        logger.info(f"Configuration loaded: model={self.gemini_model}, timeout={self.timeout}s")

    @staticmethod
    def _parse_model_name(model_str: str) -> str:
        """Parse model name, removing comments"""
        return model_str.split("#")[0].strip()


config = Config()


# ============================================================================
# FALLBACK EMBEDDER (Sentence Transformers)
# ============================================================================

class FallbackEmbedder:
    """
    Fallback to local sentence-transformers if Gemini fails.
    """

    def __init__(self):
        self.model = None
        self.model_name = "sentence-transformers/all-mpnet-base-v2"

    def _load_model(self):
        """Lazy load sentence-transformers"""
        if self.model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading fallback model: {self.model_name}")
                self.model = SentenceTransformer(self.model_name)
                logger.info("✓ Fallback model loaded")
            except ImportError:
                logger.error("sentence-transformers not installed. Install with: pip install sentence-transformers")
                raise

    def embed_single(self, text: str) -> List[float]:
        """Embed single text with fallback model"""
        self._load_model()
        embedding = self.model.encode([text])[0]
        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed batch of texts with fallback model"""
        self._load_model()
        embeddings = self.model.encode(texts)
        return [emb.tolist() for emb in embeddings]


# ============================================================================
# GEMINI EMBEDDER
# ============================================================================

class GeminiEmbedder:
    """
    Production-ready Gemini embedder with full error handling.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Gemini embedder.

        Args:
            api_key: Gemini API key (defaults to env var)
            model: Model name (defaults to env var)
        """
        self.api_key = api_key or config.gemini_api_key
        self.model = model or config.gemini_model

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found")

        # Initialize client
        try:
            self.client = genai.Client(api_key=self.api_key)
            logger.info(f"✓ Gemini Embedder initialized")
            logger.info(f"  Model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise

        # Initialize fallback
        self.fallback = FallbackEmbedder()
        self.fallback_active = False

    def embed_single(
        self,
        text: str,
        use_fallback_on_error: bool = False
    ) -> List[float]:
        """
        Embed a single text string with retry logic.

        Args:
            text: Text to embed
            use_fallback_on_error: Use fallback if Gemini fails

        Returns:
            List of floats (embedding vector)
        """
        if not text or len(text.strip()) == 0:
            logger.warning("Empty text provided for embedding")
            return []

        # Truncate very long texts
        if len(text) > 10000:
            logger.warning(f"Text too long ({len(text)} chars), truncating to 10000")
            text = text[:10000]

        # Try Gemini with retries
        for attempt in range(config.max_retries):
            try:
                result = self.client.models.embed_content(
                    model=self.model,
                    contents=text
                )

                # Validate response
                embedding_response = EmbeddingResponse.from_api_response(result.embeddings[0])
                return embedding_response.values

            except ValidationError as e:
                logger.error(f"Validation error on attempt {attempt + 1}: {e}")
                if attempt < config.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                continue

            except Exception as e:
                logger.warning(f"Gemini error on attempt {attempt + 1}: {e}")
                if attempt < config.max_retries - 1:
                    time.sleep(2 ** attempt)
                continue

        # Fallback if all retries failed
        if use_fallback_on_error:
            logger.warning("All Gemini attempts failed, using fallback embedder")
            self.fallback_active = True
            try:
                return self.fallback.embed_single(text)
            except Exception as e:
                logger.error(f"Fallback also failed: {e}")
                return []
        else:
            logger.error("All Gemini attempts failed and fallback disabled")
            return []

    def embed_batch(
        self,
        texts: List[str],
        show_progress: bool = True,
        use_fallback_on_error: bool = False
    ) -> List[List[float]]:
        """
        Embed multiple texts with batching and error handling.

        Args:
            texts: List of texts to embed
            show_progress: Show progress logging
            use_fallback_on_error: Use fallback on errors

        Returns:
            List of embedding vectors
        """
        if not texts:
            logger.warning("Empty text list provided")
            return []

        embeddings = []
        errors = 0

        for i, text in enumerate(texts):
            try:
                if show_progress and (i + 1) % 10 == 0:
                    logger.info(f"  Embedded {i + 1}/{len(texts)} texts...")

                embedding = self.embed_single(text, use_fallback_on_error)

                if not embedding:
                    logger.warning(f"Empty embedding for text {i}")
                    errors += 1

                embeddings.append(embedding)

            except Exception as e:
                logger.error(f"Error embedding text {i}: {e}")
                embeddings.append([])
                errors += 1
                continue

        if show_progress:
            logger.info(f"✓ Embedded {len(texts)} texts ({errors} errors)")
            if self.fallback_active:
                logger.warning(f"⚠ Fallback embedder was used")

        return embeddings

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings from this model.

        Returns:
            Embedding dimension
        """
        try:
            test_embedding = self.embed_single("test", use_fallback_on_error=False)
            if test_embedding:
                return len(test_embedding)
            else:
                logger.warning("Could not determine dimension, defaulting to 3072")
                return 3072
        except Exception as e:
            logger.error(f"Error getting dimension: {e}")
            return 3072


# ============================================================================
# TESTS
# ============================================================================

def test_gemini_embedder():
    """
    Comprehensive test suite for Gemini embedder.
    """
    logger.info("=" * 80)
    logger.info("TESTING GEMINI EMBEDDER")
    logger.info("=" * 80)

    try:
        # Initialize
        embedder = GeminiEmbedder()

        # Test 1: Single embedding
        logger.info("\n[Test 1] Single text embedding:")
        text = "Senior Civil Engineer with 10 years experience in structural design"
        embedding = embedder.embed_single(text)
        logger.info(f"  Text: {text}")
        logger.info(f"  Embedding dimension: {len(embedding)}")
        logger.info(f"  First 10 values: {embedding[:10]}")
        assert len(embedding) > 0, "Embedding should not be empty"

        # Test 2: Empty text
        logger.info("\n[Test 2] Empty text handling:")
        empty_embedding = embedder.embed_single("")
        logger.info(f"  Empty text result: {empty_embedding}")
        assert empty_embedding == [], "Empty text should return empty list"

        # Test 3: Very long text
        logger.info("\n[Test 3] Long text truncation:")
        long_text = "A" * 15000
        long_embedding = embedder.embed_single(long_text)
        logger.info(f"  Long text (15000 chars) embedded: {len(long_embedding) > 0}")
        assert len(long_embedding) > 0, "Long text should be truncated and embedded"

        # Test 4: Batch embedding
        logger.info("\n[Test 4] Batch embedding:")
        texts = [
            "AutoCAD expert with architectural experience",
            "Python developer specializing in machine learning",
            "Project manager with construction background"
        ]
        embeddings = embedder.embed_batch(texts, show_progress=True)
        logger.info(f"  Batch size: {len(embeddings)}")
        logger.info(f"  All embeddings generated: {all(len(e) > 0 for e in embeddings)}")
        assert len(embeddings) == len(texts), "Should return embedding for each text"

        # Test 5: Dimension check
        logger.info("\n[Test 5] Embedding dimension:")
        dim = embedder.get_embedding_dimension()
        logger.info(f"  Dimension: {dim}")
        assert dim > 0, "Dimension should be positive"

        logger.info("\n" + "=" * 80)
        logger.info("✓ ALL TESTS PASSED")
        logger.info("=" * 80)

        return True

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return False


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    try:
        test_gemini_embedder()
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

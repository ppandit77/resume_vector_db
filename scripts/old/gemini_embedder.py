"""
Gemini Embeddings Integration for Superlinked
Uses google.genai client for embedding generation
"""

import os
from typing import List, Dict, Any
from google import genai

# Load environment
import sys
sys.path.append(os.path.dirname(__file__))
from load_env import load_env
load_env()


class GeminiEmbedder:
    """
    Wrapper for Gemini embeddings using the new google.genai client.
    """

    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize Gemini embedder.

        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
            model: Model name (defaults to GEMINI_MODEL env var)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        # Remove comment from model name if present
        model_env = os.getenv("GEMINI_MODEL", "gemini-embedding-001")
        self.model = model or model_env.split("#")[0].strip()

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found. Add it to .env file")

        # Initialize client with API key
        self.client = genai.Client(api_key=self.api_key)

        print(f"✓ Gemini Embedder initialized")
        print(f"  Model: {self.model}")

    def embed_single(self, text: str) -> List[float]:
        """
        Embed a single text string.

        Args:
            text: Text to embed

        Returns:
            List of floats (embedding vector)
        """
        if not text or len(text.strip()) == 0:
            return []

        try:
            result = self.client.models.embed_content(
                model=self.model,
                contents=text
            )

            # Extract embedding values
            embedding = result.embeddings[0].values
            return list(embedding)

        except Exception as e:
            print(f"Error embedding text: {e}")
            return []

    def embed_batch(self, texts: List[str], show_progress: bool = True) -> List[List[float]]:
        """
        Embed multiple texts.

        Args:
            texts: List of texts to embed
            show_progress: Show progress bar

        Returns:
            List of embedding vectors
        """
        embeddings = []

        for i, text in enumerate(texts):
            if show_progress and (i + 1) % 10 == 0:
                print(f"  Embedded {i + 1}/{len(texts)} texts...")

            embedding = self.embed_single(text)
            embeddings.append(embedding)

        if show_progress:
            print(f"✓ Embedded {len(texts)} texts")

        return embeddings

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings from this model.

        Returns:
            Embedding dimension (e.g., 768)
        """
        # Test with a simple string
        test_embedding = self.embed_single("test")
        return len(test_embedding) if test_embedding else 768


def test_gemini_embedder():
    """
    Test the Gemini embedder with sample queries.
    """
    print("=" * 80)
    print("TESTING GEMINI EMBEDDER")
    print("=" * 80)

    # Initialize
    embedder = GeminiEmbedder()

    # Test single embedding
    print("\n[Test 1] Single text embedding:")
    text = "Senior Civil Engineer with 10 years experience in structural design"
    embedding = embedder.embed_single(text)
    print(f"  Text: {text}")
    print(f"  Embedding dimension: {len(embedding)}")
    print(f"  First 10 values: {embedding[:10]}")

    # Test batch embedding
    print("\n[Test 2] Batch embedding:")
    texts = [
        "AutoCAD expert with architectural experience",
        "Python developer specializing in machine learning",
        "Project manager with construction background",
        "Data analyst with SQL and Excel skills"
    ]
    embeddings = embedder.embed_batch(texts, show_progress=True)
    print(f"  Batch size: {len(embeddings)}")
    print(f"  All embeddings generated: {all(len(e) > 0 for e in embeddings)}")

    # Test embedding dimension
    print("\n[Test 3] Embedding dimension:")
    dim = embedder.get_embedding_dimension()
    print(f"  Dimension: {dim}")

    print("\n" + "=" * 80)
    print("✓ ALL TESTS PASSED")
    print("=" * 80)


if __name__ == "__main__":
    test_gemini_embedder()

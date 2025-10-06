"""Simple .env file loader (no external dependencies needed)"""
import os

def load_env(env_file=".env"):
    """Load environment variables from .env file."""
    if not os.path.exists(env_file):
        return

    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue

            # Parse KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                # Set environment variable
                os.environ[key] = value
                print(f"✓ Loaded {key}")

if __name__ == "__main__":
    load_env()
    print(f"\nOPENAI_API_KEY: {os.getenv('OPENAI_API_KEY', 'NOT SET')}")
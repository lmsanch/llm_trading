"""Configuration for the LLM Council and LLM Trading."""

import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# OpenRouter Configuration
# ============================================================================

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Council members - list of OpenRouter model identifiers
COUNCIL_MODELS = [
    "openai/gpt-5.1",
    "google/gemini-3-pro-preview",
    "anthropic/claude-sonnet-4.5",
    "x-ai/grok-4",
]

# Chairman model - synthesizes final response
CHAIRMAN_MODEL = "google/gemini-3-pro-preview"

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Data directory for conversation storage
DATA_DIR = "data/conversations"

# ============================================================================
# Port Configuration
# ============================================================================

def get_port(env_var: str, default: int) -> int:
    """Get port from environment or return default."""
    try:
        return int(os.getenv(env_var, default))
    except ValueError:
        print(f"Warning: Invalid {env_var}, using default {default}")
        return default

# Backend API server port
BACKEND_PORT = get_port("PORT_BACKEND", 8200)

# Frontend dev server port
FRONTEND_PORT = get_port("PORT_FRONTEND", 4173)

# Test utilities port
TEST_PORT = get_port("PORT_TEST", 8201)

# PostgreSQL port (future use)
POSTGRES_PORT = get_port("PORT_POSTGRES", 5432)

# Tailscale IP for CORS
TAILSCALE_IP = os.getenv("TAILSCALE_IP", "100.100.238.72")

def get_cors_origins():
    """Generate CORS allowed origins based on port configuration."""
    return [
        f"http://localhost:{FRONTEND_PORT}",
        f"http://{TAILSCALE_IP}:{FRONTEND_PORT}",
    ]

# ============================================================================
# PostgreSQL / Database Configuration
# ============================================================================

# Database connection parameters
DATABASE_URL = os.getenv("DATABASE_URL")  # Full connection string (optional)
DATABASE_NAME = os.getenv("DATABASE_NAME", "llm_trading")
DATABASE_USER = os.getenv("DATABASE_USER", "luis")
DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
DATABASE_PORT = get_port("DATABASE_PORT", 5432)
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")  # Optional

# Connection pool configuration
DB_MIN_POOL_SIZE = int(os.getenv("DB_MIN_POOL_SIZE", "10"))
DB_MAX_POOL_SIZE = int(os.getenv("DB_MAX_POOL_SIZE", "50"))
DB_COMMAND_TIMEOUT = float(os.getenv("DB_COMMAND_TIMEOUT", "60.0"))
DB_MAX_QUERIES = int(os.getenv("DB_MAX_QUERIES", "50000"))
DB_MAX_INACTIVE_CONNECTION_LIFETIME = float(os.getenv("DB_MAX_INACTIVE_CONNECTION_LIFETIME", "300.0"))

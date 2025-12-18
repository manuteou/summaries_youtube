# constants.py - Centralized configuration constants
"""
Ce module centralise toutes les constantes du projet pour faciliter
la maintenance et éviter les "magic numbers" dispersés dans le code.
"""

# =============================================================================
# VIDEO FILTERING
# =============================================================================
MIN_VIDEO_DURATION_SECONDS = 120  # Durée minimum pour éviter les shorts
SHORT_VIDEO_MAX_SECONDS = 300     # < 5 min = vidéo courte
MEDIUM_VIDEO_MAX_SECONDS = 1200   # 5-20 min = vidéo moyenne
# > 20 min = vidéo longue

# =============================================================================
# AUDIO PROCESSING
# =============================================================================
SEGMENT_LENGTH_MS = 10 * 60 * 1000  # 10 minutes en millisecondes
DEFAULT_AUDIO_SAMPLE_RATE = 16000
AUDIO_COMPRESSION_LEVEL = 0

# =============================================================================
# LLM CONFIGURATION
# =============================================================================
DEFAULT_CONTEXT_SIZE = 8192
DEFAULT_NUM_PREDICT = -1  # Pas de limite

# =============================================================================
# CHUNK SIZES BY SUMMARY TYPE
# =============================================================================
CHUNK_SIZES = {
    "short": 6000,
    "medium": 20000,
    "long": 10000,
    "news": 15000,
    "meeting": 12000,
}

# =============================================================================
# SEARCH CONFIGURATION
# =============================================================================
MIN_RESULTS_TARGET = 5
MIN_BOOSTED_SOURCES = 2
MAX_FETCH_ATTEMPTS = 3
THREAD_POOL_SIZE = 20

# =============================================================================
# RETRY CONFIGURATION
# =============================================================================
MAX_DOWNLOAD_RETRIES = 3
RETRY_DELAY_SECONDS = 2

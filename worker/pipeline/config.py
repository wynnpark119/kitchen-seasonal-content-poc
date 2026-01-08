"""
Pipeline configuration constants
"""
# Collection limits
MAX_POSTS_PER_KEYWORD = 1000
TOP_COMMENTS_PER_POST = 3
REPRESENTATIVE_SAMPLES_K = 5
MAX_BRIEFS_TO_GENERATE = 50

# Embedding settings
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIM = 3072  # text-embedding-3-large default dimension

# Clustering settings
HDBSCAN_MIN_CLUSTER_SIZE = 5
HDBSCAN_MIN_SAMPLES = 3
HDBSCAN_METRIC = "euclidean"

# LLM settings
LLM_MODEL = "gpt-4o-mini"
LLM_MODEL_VERSION = "1.0"
LLM_MAX_RETRIES = 2
LLM_TEMPERATURE = 0.3

# Keywords extraction
TOP_KEYWORDS_COUNT = 15

# Timeseries
TIMESERIES_MONTHS_BACK = 12  # Last 12 months

# Retry settings
API_MAX_RETRIES = 3
API_BACKOFF_FACTOR = 2  # Exponential backoff

# Categories
CATEGORIES = [
    "SPRING_RECIPES",
    "SPRING_KITCHEN_STYLING",
    "REFRIGERATOR_ORGANIZATION",
    "VEGETABLE_PREP_HANDLING"
]

# Reddit keywords by category
REDDIT_KEYWORDS = {
    "SPRING_RECIPES": [
        "spring recipes", "spring cooking", "spring meal prep",
        "spring vegetables", "seasonal cooking", "light spring meals",
        "spring dinner ideas", "spring lunch recipes"
    ],
    "SPRING_KITCHEN_STYLING": [
        "spring kitchen decor", "spring kitchen styling",
        "kitchen spring refresh", "spring table setting",
        "spring home decor kitchen"
    ],
    "REFRIGERATOR_ORGANIZATION": [
        "refrigerator organization", "fridge organization",
        "refrigerator storage", "fridge cleaning tips",
        "refrigerator meal prep organization"
    ],
    "VEGETABLE_PREP_HANDLING": [
        "vegetable prep", "vegetable storage",
        "how to prep vegetables", "vegetable cleaning",
        "meal prep vegetables", "vegetable handling"
    ]
}

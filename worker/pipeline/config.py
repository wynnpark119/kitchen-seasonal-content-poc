"""
Pipeline configuration constants
"""
import os

# Collection limits
# 본격 수집: 각 키워드당 최대 1000개 포스트
MAX_POSTS_PER_KEYWORD = 1000  # 본격 수집: 1000개
TOP_COMMENTS_PER_POST = 3
REPRESENTATIVE_SAMPLES_K = 5
MAX_BRIEFS_TO_GENERATE = 50

# Preprocessing settings
MIN_TEXT_LENGTH = 30  # 최소 텍스트 길이 (30자 이하 제거)

# Embedding settings
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIM = 3072  # text-embedding-3-large default dimension
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "64"))
DB_WRITE_CONCURRENCY = int(os.getenv("DB_WRITE_CONCURRENCY", "3"))  # 동시 DB write 제한
DB_BATCH_SIZE = int(os.getenv("DB_BATCH_SIZE", "100"))  # DB 저장 배치 크기
DB_POOL_MINCONN = int(os.getenv("DB_POOL_MINCONN", "5"))
DB_POOL_MAXCONN = int(os.getenv("DB_POOL_MAXCONN", "20"))
DB_POOL_ACQUIRE_TIMEOUT = float(os.getenv("DB_POOL_ACQUIRE_TIMEOUT", "10.0"))
DB_ALLOW_DIRECT_FALLBACK = os.getenv("DB_ALLOW_DIRECT_FALLBACK", "false").lower() == "true"

# Clustering settings
HDBSCAN_MIN_CLUSTER_SIZE = 10  # 최소 클러스터 크기
HDBSCAN_MIN_SAMPLES = 5  # 최소 샘플 수
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

# SERP AIO 샘플 쿼리 (각 대주제 1개씩, 비용 최소화)
SERP_AIO_SAMPLE_QUERIES = {
    "SPRING_RECIPES": "spring dinner ideas",
    "SPRING_KITCHEN_STYLING": "spring kitchen decor",
    "REFRIGERATOR_ORGANIZATION": "refrigerator organization",
    "VEGETABLE_PREP_HANDLING": "vegetable prep"
}

# Categories
CATEGORIES = [
    "SPRING_RECIPES",
    "SPRING_KITCHEN_STYLING",
    "REFRIGERATOR_ORGANIZATION",
    "VEGETABLE_PREP_HANDLING"
]

# 카테고리별 시즌성 분류
SEASONAL_CATEGORIES = [
    "SPRING_RECIPES",
    "SPRING_KITCHEN_STYLING"
]

EVERGREEN_CATEGORIES = [
    "REFRIGERATOR_ORGANIZATION",
    "VEGETABLE_PREP_HANDLING"
]

# Reddit keywords by category (실사용 빈도 기반, Reddit 실제 질문/토론 패턴 반영)
# 테스트용: 각 카테고리별 TOP TIER 키워드만 선택 (전체 수집 시 주석 해제)
REDDIT_KEYWORDS = {
    "SPRING_RECIPES": [
        # TOP TIER (실제 질문 제목에 가장 자주 등장) - 테스트용으로 일부만
        "spring dinner ideas",
        "easy spring meals",
        "what to cook in spring",
        "spring meal prep",
        "light spring recipes",
        "quick spring dinner",
        "spring weeknight meals",
        "healthy spring meals",
        # "spring comfort food",
        # "simple spring recipes",
        # "spring cooking ideas",
        # "spring dinner recipes",
        # MID TIER (보조 확장) - 테스트용으로 주석 처리
        # "spring lunch ideas",
        # "spring breakfast recipes",
        # "meal prep spring vegetables",
        # "spring pasta recipes",
        # "spring salad ideas",
        # "spring soup recipes",
        # "spring casserole recipes",
        # "spring one pot meals",
        # "spring slow cooker recipes",
        # "spring sheet pan meals",
        # "spring vegetarian meals",
        # "spring family dinners",
        # LONG-TAIL 질문형 (실제 Reddit 질문 제목과 유사) - 테스트용으로 일부만
        "what do you cook in spring",
        "best spring dinner ideas"
        # "anyone else meal prep for spring",
        # "how do you use spring vegetables",
        # "what's your favorite spring meal",
        # "best way to cook spring vegetables"
    ],
    "SPRING_KITCHEN_STYLING": [
        # TOP TIER
        "spring kitchen decor",
        "kitchen spring refresh",
        "spring table setting ideas",
        "how to decorate kitchen for spring",
        "spring kitchen ideas",
        "kitchen spring makeover",
        "spring kitchen styling",
        "spring home decor kitchen",
        "spring kitchen update",
        "spring kitchen refresh ideas",
        "spring kitchen decoration",
        "spring kitchen design ideas",
        # MID TIER
        "spring kitchen colors",
        "spring kitchen accessories",
        "spring kitchen centerpiece",
        "spring kitchen window decor",
        "spring kitchen counter decor",
        "spring kitchen wall decor",
        "spring kitchen lighting",
        "spring kitchen plants",
        "spring kitchen organization decor",
        "spring kitchen rug",
        "spring kitchen curtains",
        "spring kitchen art",
        # LONG-TAIL 질문형
        "how do you decorate your kitchen for spring",
        "what spring decor do you use in kitchen",
        "anyone else refresh kitchen for spring",
        "best way to style kitchen for spring",
        "what spring colors work in kitchen",
        "how do you make kitchen feel spring"
    ],
    "REFRIGERATOR_ORGANIZATION": [
        # TOP TIER
        "refrigerator organization",
        "fridge organization tips",
        "how to organize refrigerator",
        "refrigerator storage ideas",
        "fridge organization system",
        "refrigerator organization hacks",
        "how do you organize your fridge",
        "fridge organization methods",
        "refrigerator organization tips",
        "fridge storage organization",
        "refrigerator organization ideas",
        "best way to organize fridge",
        # MID TIER
        "refrigerator drawer organization",
        "fridge shelf organization",
        "refrigerator door organization",
        "fridge organization containers",
        "refrigerator organization bins",
        "fridge organization labels",
        "refrigerator organization system",
        "fridge organization routine",
        "refrigerator organization before after",
        "fridge organization meal prep",
        "refrigerator organization small fridge",
        "fridge organization family",
        # LONG-TAIL 질문형
        "how do you organize your refrigerator",
        "what's the best way to organize fridge",
        "anyone else struggle with fridge organization",
        "how do you keep fridge organized",
        "what do you use to organize fridge",
        "best tips for refrigerator organization"
    ],
    "VEGETABLE_PREP_HANDLING": [
        # TOP TIER
        "vegetable prep",
        "how to prep vegetables",
        "vegetable storage tips",
        "how to store vegetables",
        "vegetable washing tips",
        "how to wash vegetables",
        "vegetable prep meal prep",
        "best way to prep vegetables",
        "vegetable handling tips",
        "how to clean vegetables",
        "vegetable prep ideas",
        "vegetable storage methods",
        # MID TIER
        "vegetable prep containers",
        "vegetable storage containers",
        "how to store cut vegetables",
        "vegetable prep ahead",
        "vegetable washing methods",
        "vegetable prep for meal prep",
        "vegetable storage fridge",
        "vegetable prep routine",
        "vegetable washing techniques",
        "vegetable prep tips",
        "vegetable storage hacks",
        "vegetable prep organization",
        # LONG-TAIL 질문형
        "how do you prep vegetables",
        "what's the best way to prep vegetables",
        "how do you wash vegetables",
        "anyone else prep vegetables ahead",
        "how do you store vegetables",
        "best way to store cut vegetables"
    ]
}

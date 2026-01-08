"""
Pydantic models for LLM output validation
"""
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

class TopicQABrief(BaseModel):
    """LLM output schema for topic Q&A brief"""
    category: str = Field(..., description="One of 4 main categories")
    topic_title: str = Field(..., max_length=500, description="Topic title in Korean")
    primary_question: str = Field(..., description="Primary question in Korean")
    related_questions: List[str] = Field(default_factory=list, description="Related questions in Korean")
    blog_angle: Optional[str] = Field(None, description="Blog content angle in Korean")
    social_angle: Optional[str] = Field(None, description="Social media content angle in Korean")
    why_now: Optional[dict] = Field(None, description="Why now explanation as structured data")
    evidence_summary: Optional[str] = Field(None, description="Evidence pack summary in Korean")
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str) -> str:
        valid_categories = [
            "SPRING_RECIPES",
            "SPRING_KITCHEN_STYLING",
            "REFRIGERATOR_ORGANIZATION",
            "VEGETABLE_PREP_HANDLING"
        ]
        if v not in valid_categories:
            raise ValueError(f"category must be one of {valid_categories}")
        return v

"""
AI Service - Unified abstraction layer for LLM providers

Supports:
- OpenAI GPT-4o (primary)
- Claude Sonnet 4 (fallback/variants)
- OpenRouter (future)

Designed for structured landing page generation.
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import uuid
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


# ==================== ENUMS & MODELS ====================

class AIProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"


class AIModel(str, Enum):
    # OpenAI
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4.1-mini"
    GPT_5_2 = "gpt-5.2"
    # Anthropic
    CLAUDE_SONNET_4 = "claude-4-sonnet-20250514"
    CLAUDE_SONNET_45 = "claude-sonnet-4-5-20250929"
    # Default
    DEFAULT = "gpt-4o"


class LandingPageSection(BaseModel):
    """A single section of a landing page"""
    type: str  # hero, features, benefits, social_proof, faq, cta, etc.
    order: int
    headline: Optional[str] = None
    subheadline: Optional[str] = None
    body_text: Optional[str] = None
    items: Optional[List[Dict[str, Any]]] = None  # For lists of features, benefits, FAQs
    cta_text: Optional[str] = None
    cta_url: Optional[str] = None
    image_placeholder: Optional[str] = None  # Description for image
    metadata: Optional[Dict[str, Any]] = None


class LandingPageSchema(BaseModel):
    """Structured output for a generated landing page"""
    page_title: str
    meta_description: str
    sections: List[LandingPageSection]
    color_scheme: Optional[Dict[str, str]] = None
    conversion_rationale: Optional[str] = None  # For internal review
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ==================== AI SERVICE CLASS ====================

class AIService:
    """Unified AI service for landing page generation"""
    
    def __init__(
        self,
        provider: AIProvider = AIProvider.OPENAI,
        model: str = AIModel.GPT_4O.value,
        api_key: Optional[str] = None
    ):
        self.provider = provider
        self.model = model
        self.api_key = api_key or os.environ.get("EMERGENT_LLM_KEY")
        
        if not self.api_key:
            raise ValueError("No API key provided. Set EMERGENT_LLM_KEY environment variable.")
    
    async def generate_landing_page(
        self,
        page_goal: str,
        target_audience: str,
        offer_details: str,
        cta_type: str = "signup",
        tone: str = "professional",
        brand_name: Optional[str] = None,
        brand_colors: Optional[Dict[str, str]] = None,
        brand_voice: Optional[str] = None,
        affiliate_program: Optional[Dict[str, Any]] = None,
        product_features: Optional[List[str]] = None,
        testimonials: Optional[List[Dict[str, str]]] = None,
        additional_context: Optional[str] = None
    ) -> LandingPageSchema:
        """Generate a structured landing page using AI"""
        
        # Build the prompt
        prompt = self._build_generation_prompt(
            page_goal=page_goal,
            target_audience=target_audience,
            offer_details=offer_details,
            cta_type=cta_type,
            tone=tone,
            brand_name=brand_name,
            brand_colors=brand_colors,
            brand_voice=brand_voice,
            affiliate_program=affiliate_program,
            product_features=product_features,
            testimonials=testimonials,
            additional_context=additional_context
        )
        
        # Generate content using LlmChat
        response_text = await self._call_llm(prompt)
        
        # Parse the response
        page_schema = self._parse_response(response_text)
        
        return page_schema
    
    async def rewrite_section(
        self,
        section: LandingPageSection,
        instruction: str,
        tone: str = "professional"
    ) -> LandingPageSection:
        """Rewrite a single section with Claude (fallback model)"""
        
        prompt = f"""Rewrite the following landing page section according to these instructions:

Instruction: {instruction}
Tone: {tone}

Original Section:
- Type: {section.type}
- Headline: {section.headline or 'N/A'}
- Subheadline: {section.subheadline or 'N/A'}
- Body: {section.body_text or 'N/A'}
- CTA: {section.cta_text or 'N/A'}

Respond with JSON only:
{{
  "type": "{section.type}",
  "order": {section.order},
  "headline": "new headline",
  "subheadline": "new subheadline",
  "body_text": "new body text",
  "cta_text": "new cta text"
}}"""
        
        # Use Claude for rewrites
        response_text = await self._call_llm(prompt, use_fallback=True)
        
        try:
            # Find JSON in response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                data = json.loads(json_str)
                return LandingPageSection(**data)
        except Exception as e:
            logger.error(f"Failed to parse rewrite response: {e}")
        
        return section
    
    async def generate_variants(
        self,
        page_schema: LandingPageSchema,
        num_variants: int = 3
    ) -> List[LandingPageSchema]:
        """Generate headline/CTA variants for A/B testing"""
        
        variants = []
        original_hero = next((s for s in page_schema.sections if s.type == "hero"), None)
        
        if not original_hero:
            return [page_schema]
        
        prompt = f"""Generate {num_variants} alternative headlines and CTAs for this landing page:

Original:
- Headline: {original_hero.headline}
- Subheadline: {original_hero.subheadline}
- CTA: {original_hero.cta_text}

Provide {num_variants} variants as JSON array:
[
  {{
    "headline": "variant headline 1",
    "subheadline": "variant subheadline 1",
    "cta_text": "variant cta 1"
  }}
]"""
        
        response_text = await self._call_llm(prompt, use_fallback=True)
        
        try:
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                variant_data = json.loads(json_str)
                
                for i, v in enumerate(variant_data[:num_variants]):
                    new_schema = page_schema.copy(deep=True)
                    for section in new_schema.sections:
                        if section.type == "hero":
                            section.headline = v.get("headline", section.headline)
                            section.subheadline = v.get("subheadline", section.subheadline)
                            section.cta_text = v.get("cta_text", section.cta_text)
                    variants.append(new_schema)
        except Exception as e:
            logger.error(f"Failed to generate variants: {e}")
        
        return variants if variants else [page_schema]
    
    def _build_generation_prompt(
        self,
        page_goal: str,
        target_audience: str,
        offer_details: str,
        cta_type: str,
        tone: str,
        brand_name: Optional[str],
        brand_colors: Optional[Dict[str, str]],
        brand_voice: Optional[str],
        affiliate_program: Optional[Dict[str, Any]],
        product_features: Optional[List[str]],
        testimonials: Optional[List[Dict[str, str]]],
        additional_context: Optional[str]
    ) -> str:
        
        prompt = f"""You are an expert conversion copywriter. Generate a high-converting landing page structure.

## PAGE REQUIREMENTS
- Goal: {page_goal}
- Target Audience: {target_audience}
- Offer: {offer_details}
- CTA Type: {cta_type}
- Tone: {tone}
"""
        
        if brand_name:
            prompt += f"\n## BRAND\n- Name: {brand_name}\n"
            if brand_colors:
                prompt += f"- Colors: {json.dumps(brand_colors)}\n"
            if brand_voice:
                prompt += f"- Voice: {brand_voice}\n"
        
        if affiliate_program:
            prompt += f"""\n## AFFILIATE PROGRAM
- Program: {affiliate_program.get('name', 'Affiliate Program')}
- Commission: {affiliate_program.get('commission_type', 'percentage')} - {affiliate_program.get('commission_value', '10')}{'%' if affiliate_program.get('commission_type') == 'percentage' else ''}
- Cookie Duration: {affiliate_program.get('cookie_duration_days', 30)} days
"""
        
        if product_features:
            prompt += f"\n## PRODUCT FEATURES\n" + "\n".join(f"- {f}" for f in product_features)
        
        if testimonials:
            prompt += f"\n## TESTIMONIALS (Use for social proof)\n"
            for t in testimonials[:3]:
                prompt += f"- \"{t.get('quote', '')}\" - {t.get('name', 'Customer')}\n"
        
        if additional_context:
            prompt += f"\n## ADDITIONAL CONTEXT\n{additional_context}\n"
        
        prompt += """

## OUTPUT FORMAT
Respond with ONLY valid JSON in this exact structure:
{
  "page_title": "SEO-optimized page title",
  "meta_description": "Meta description under 160 chars",
  "sections": [
    {
      "type": "hero",
      "order": 1,
      "headline": "Main headline (powerful, benefit-focused)",
      "subheadline": "Supporting subheadline",
      "body_text": "Brief intro paragraph",
      "cta_text": "Call to action button text",
      "cta_url": "#signup",
      "image_placeholder": "Description of hero image"
    },
    {
      "type": "features",
      "order": 2,
      "headline": "Section headline",
      "items": [
        {"title": "Feature 1", "description": "Description", "icon": "star"},
        {"title": "Feature 2", "description": "Description", "icon": "check"},
        {"title": "Feature 3", "description": "Description", "icon": "zap"}
      ]
    },
    {
      "type": "benefits",
      "order": 3,
      "headline": "Why Choose Us",
      "items": [
        {"title": "Benefit 1", "description": "Detailed benefit description"},
        {"title": "Benefit 2", "description": "Detailed benefit description"},
        {"title": "Benefit 3", "description": "Detailed benefit description"}
      ]
    },
    {
      "type": "social_proof",
      "order": 4,
      "headline": "What Our Customers Say",
      "items": [
        {"quote": "Testimonial quote", "name": "Customer Name", "title": "Job Title"},
        {"quote": "Another quote", "name": "Another Name", "title": "Job Title"}
      ]
    },
    {
      "type": "faq",
      "order": 5,
      "headline": "Frequently Asked Questions",
      "items": [
        {"question": "Common question?", "answer": "Clear answer"},
        {"question": "Another question?", "answer": "Another answer"}
      ]
    },
    {
      "type": "cta",
      "order": 6,
      "headline": "Final compelling headline",
      "subheadline": "Urgency or value reinforcement",
      "cta_text": "Strong call to action",
      "cta_url": "#signup"
    }
  ],
  "color_scheme": {
    "primary": "#hexcode",
    "secondary": "#hexcode",
    "accent": "#hexcode",
    "background": "#hexcode",
    "text": "#hexcode"
  },
  "conversion_rationale": "Brief explanation of copywriting strategy used"
}

IMPORTANT: Return ONLY the JSON, no markdown, no explanation."""
        
        return prompt
    
    async def _call_llm(self, prompt: str, use_fallback: bool = False) -> str:
        """Call the LLM using emergentintegrations"""
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        session_id = f"landing-page-{uuid.uuid4().hex[:8]}"
        
        # Determine provider and model
        if use_fallback:
            provider = "anthropic"
            model = AIModel.CLAUDE_SONNET_4.value
        else:
            provider = "openai"
            model = self.model
        
        chat = LlmChat(
            api_key=self.api_key,
            session_id=session_id,
            system_message="You are an expert conversion copywriter and landing page designer. Always respond with valid JSON when requested."
        ).with_model(provider, model)
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        return response
    
    def _parse_response(self, response_text: str) -> LandingPageSchema:
        """Parse AI response into LandingPageSchema"""
        try:
            # Find JSON in response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                data = json.loads(json_str)
                
                # Convert sections to LandingPageSection objects
                sections = []
                for s in data.get("sections", []):
                    sections.append(LandingPageSection(**s))
                
                return LandingPageSchema(
                    page_title=data.get("page_title", "Landing Page"),
                    meta_description=data.get("meta_description", ""),
                    sections=sections,
                    color_scheme=data.get("color_scheme"),
                    conversion_rationale=data.get("conversion_rationale")
                )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.error(f"Response: {response_text[:500]}")
        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
        
        # Return default schema on failure
        return LandingPageSchema(
            page_title="Landing Page",
            meta_description="",
            sections=[
                LandingPageSection(
                    type="hero",
                    order=1,
                    headline="Welcome",
                    subheadline="We couldn't generate the page. Please try again.",
                    cta_text="Get Started"
                )
            ]
        )


# Factory function
def get_ai_service(
    provider: str = "openai",
    model: str = "gpt-4o"
) -> AIService:
    """Get an AI service instance"""
    return AIService(
        provider=AIProvider(provider),
        model=model
    )

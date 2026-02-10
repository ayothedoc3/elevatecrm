"""
AI Service - Unified abstraction layer for LLM providers

Supports:
- OpenAI GPT-4o (direct API)
- Claude via OpenRouter (OpenAI-compatible API)
- Any OpenRouter model

Uses the official OpenAI SDK for all providers (OpenRouter is OpenAI-compatible).
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
from openai import AsyncOpenAI

load_dotenv()

logger = logging.getLogger(__name__)


# ==================== ENUMS & MODELS ====================

class AIProvider(str, Enum):
    OPENAI = "openai"
    OPENROUTER = "openrouter"


class AIModel(str, Enum):
    # OpenAI
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4_1 = "gpt-4.1"
    GPT_4_1_MINI = "gpt-4.1-mini"
    # Claude (via OpenRouter)
    CLAUDE_SONNET_4 = "anthropic/claude-sonnet-4"
    CLAUDE_SONNET_45 = "anthropic/claude-sonnet-4.5"
    CLAUDE_HAIKU = "anthropic/claude-3-5-haiku"
    # Default
    DEFAULT = "gpt-4o"


# Model -> provider mapping for auto-detection
OPENROUTER_MODELS = {
    "anthropic/claude-sonnet-4",
    "anthropic/claude-sonnet-4.5",
    "anthropic/claude-3-5-haiku",
}

OPENAI_MODELS = {
    "gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini",
}


def _resolve_provider_and_client(model: str) -> tuple:
    """Given a model name, return (provider, client) using the right API key and base URL."""
    if model in OPENROUTER_MODELS or model.startswith("anthropic/"):
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENROUTER_API_KEY is required for Claude models. "
                "Get one at https://openrouter.ai/keys"
            )
        client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )
        return "openrouter", client
    else:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is required for OpenAI models. "
                "Get one at https://platform.openai.com/api-keys"
            )
        client = AsyncOpenAI(api_key=api_key)
        return "openai", client


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
        # api_key param is kept for backward compat but we resolve per-call now
        self._explicit_key = api_key

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

        response_text = await self._call_llm(prompt)
        page_schema = self._parse_response(response_text)

        return page_schema

    async def rewrite_section(
        self,
        section: LandingPageSection,
        instruction: str,
        tone: str = "professional"
    ) -> LandingPageSection:
        """Rewrite a single section"""

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

        response_text = await self._call_llm(prompt, use_fallback=True)

        try:
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

    async def _call_llm(self, prompt: str, use_fallback: bool = False, model_override: str = None) -> str:
        """Call the LLM using OpenAI SDK (works for both OpenAI and OpenRouter)"""

        model = model_override or self.model

        # For fallback, use Claude via OpenRouter
        if use_fallback and model not in OPENROUTER_MODELS:
            model = AIModel.CLAUDE_SONNET_4.value

        provider, client = _resolve_provider_and_client(model)

        extra_headers = {}
        if provider == "openrouter":
            extra_headers = {
                "HTTP-Referer": "https://elevatecrm.app",
                "X-Title": "Elevate CRM Page Builder",
            }

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert conversion copywriter and landing page designer. Always respond with valid JSON when requested."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000,
            extra_headers=extra_headers if extra_headers else None,
        )

        return response.choices[0].message.content

    def _parse_response(self, response_text: str) -> LandingPageSchema:
        """Parse AI response into LandingPageSchema"""
        try:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                data = json.loads(json_str)

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


    async def chat_with_context(
        self,
        conversation_history: List[Dict[str, str]],
        current_schema: Optional[Dict[str, Any]],
        user_message: str,
        selected_section_index: Optional[int] = None,
        page_context: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Conversational page builder - handles iterative chat messages"""

        # Build system prompt
        system_prompt = """You are an expert landing page builder assistant. You help users create and iterate on high-converting landing pages through conversation.

RULES:
1. When the user asks you to create a page, modify content, add/remove sections, or change styling, respond with BOTH a conversational explanation AND the updated page schema.
2. Separate your conversational response from the schema using exactly this delimiter on its own line: ---SCHEMA---
3. The schema must be valid JSON matching this format:
{
  "page_title": "string",
  "meta_description": "string",
  "sections": [{"type": "hero|features|benefits|social_proof|faq|cta", "order": 1, "headline": "...", "subheadline": "...", "body_text": "...", "items": [...], "cta_text": "...", "cta_url": "..."}],
  "color_scheme": {"primary": "#hex", "secondary": "#hex", "accent": "#hex", "background": "#hex", "text": "#hex"}
}
4. ALWAYS return the COMPLETE page schema with ALL sections, not just the modified one.
5. If the user asks a question or gives feedback that doesn't require page changes, just respond conversationally WITHOUT the ---SCHEMA--- delimiter.
6. Supported section types: hero, features, benefits, social_proof, faq, cta
7. Keep section order integers sequential starting from 1.
8. Generate compelling, conversion-focused copy. Be creative with headlines and descriptions.
9. When creating a new page, always include at least: hero, features, benefits, and cta sections."""

        # Add current page state to system prompt
        if current_schema:
            system_prompt += f"\n\nCURRENT PAGE STATE:\n{json.dumps(current_schema, indent=2)}"
        else:
            system_prompt += "\n\nCURRENT PAGE STATE: No page has been created yet. The user wants to build a new landing page."

        if selected_section_index is not None and current_schema:
            sections = current_schema.get("sections", [])
            if 0 <= selected_section_index < len(sections):
                section = sections[selected_section_index]
                system_prompt += f"\n\nSELECTED SECTION: Index {selected_section_index} ({section.get('type', 'unknown')}) - The user has selected this section. Focus modifications on it unless they ask for something else."

        if page_context:
            ctx_parts = []
            if page_context.get("brand_name"):
                ctx_parts.append(f"Brand: {page_context['brand_name']}")
            if page_context.get("tone"):
                ctx_parts.append(f"Tone: {page_context['tone']}")
            if page_context.get("page_type"):
                ctx_parts.append(f"Page Type: {page_context['page_type']}")
            if ctx_parts:
                system_prompt += f"\n\nPAGE CONTEXT: {', '.join(ctx_parts)}"

        # Build messages array for the chat completion
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history as proper message turns
        for msg in conversation_history[-20:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "assistant":
                # Strip schema from assistant history to save tokens
                content = content.split("---SCHEMA---")[0].strip() if "---SCHEMA---" in content else content
            messages.append({"role": role, "content": content})

        # Add the new user message
        messages.append({"role": "user", "content": user_message})

        # Resolve provider and client based on model
        provider, client = _resolve_provider_and_client(self.model)

        extra_headers = {}
        if provider == "openrouter":
            extra_headers = {
                "HTTP-Referer": "https://elevatecrm.app",
                "X-Title": "Elevate CRM Page Builder",
            }

        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=4000,
            extra_headers=extra_headers if extra_headers else None,
        )

        response_text = response.choices[0].message.content

        # Parse the response
        return self._parse_chat_response(response_text, current_schema)

    def _parse_chat_response(self, response_text: str, old_schema: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Parse chat response, separating text from schema"""
        DELIMITER = "---SCHEMA---"

        if DELIMITER in response_text:
            parts = response_text.split(DELIMITER, 1)
            text_part = parts[0].strip()
            schema_part = parts[1].strip()

            # Extract JSON from schema part
            try:
                json_start = schema_part.find('{')
                json_end = schema_part.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = schema_part[json_start:json_end]
                    updated_schema = json.loads(json_str)

                    # Validate sections have valid types
                    valid_types = {"hero", "features", "benefits", "social_proof", "faq", "cta"}
                    if "sections" in updated_schema:
                        updated_schema["sections"] = [
                            s for s in updated_schema["sections"]
                            if s.get("type") in valid_types
                        ]

                    # Determine action
                    action = "generate" if old_schema is None else "modify"

                    # Find modified sections
                    modified_sections = []
                    if old_schema and "sections" in old_schema:
                        old_sections = old_schema.get("sections", [])
                        new_sections = updated_schema.get("sections", [])
                        for i, ns in enumerate(new_sections):
                            if i >= len(old_sections):
                                modified_sections.append(i)
                            elif json.dumps(ns, sort_keys=True) != json.dumps(old_sections[i], sort_keys=True):
                                modified_sections.append(i)
                    else:
                        modified_sections = list(range(len(updated_schema.get("sections", []))))

                    return {
                        "response_text": text_part,
                        "updated_schema": updated_schema,
                        "action": action,
                        "modified_sections": modified_sections
                    }
            except (json.JSONDecodeError, Exception) as e:
                logger.error(f"Failed to parse chat schema: {e}")
                return {
                    "response_text": text_part + "\n\n(I tried to update the page but encountered a formatting issue. Could you try rephrasing your request?)",
                    "updated_schema": None,
                    "action": "error",
                    "modified_sections": []
                }

        # No schema delimiter - just a conversational response
        return {
            "response_text": response_text.strip(),
            "updated_schema": None,
            "action": "message",
            "modified_sections": []
        }


# Factory function
def get_ai_service(
    provider: str = "openai",
    model: str = "gpt-4o"
) -> AIService:
    """Get an AI service instance"""
    return AIService(
        provider=AIProvider(provider) if provider in [p.value for p in AIProvider] else AIProvider.OPENAI,
        model=model
    )

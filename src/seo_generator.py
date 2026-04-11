"""
SEO Content Generator Module
Uses Google Gemini AI to generate optimized titles, descriptions, and tags
for re-uploaded trailer videos.
"""

import logging
from typing import Optional

import google.generativeai as genai

import config

logger = logging.getLogger(__name__)

# System prompt for SEO content generation
SEO_SYSTEM_PROMPT = """You are an expert YouTube SEO content writer specializing in movie trailers. 
Your task is to generate optimized YouTube metadata for re-uploaded movie trailers.

Rules:
1. Title must be catchy, SEO-optimized, and include the movie name + "Official Trailer" or "Teaser"
2. Description must be engaging, include keywords naturally, and have proper hashtags
3. Tags must be relevant, trending, and optimized for YouTube search
4. Do NOT use any misleading clickbait
5. Keep titles under 100 characters for best visibility
6. Description should be 200-500 words with relevant keywords
7. Generate 15-20 tags
8. Include relevant hashtags in description (max 5)
9. Always respond in valid JSON format only

Respond with ONLY a JSON object in this exact format:
{
    "title": "Your SEO Title Here",
    "description": "Your SEO description here with hashtags",
    "tags": ["tag1", "tag2", "tag3"]
}"""


class SEOGenerator:
    """Generates SEO-optimized YouTube metadata using Gemini AI."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.GEMINI_API_KEY
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                system_instruction=SEO_SYSTEM_PROMPT
            )
            logger.info("Gemini AI initialized for SEO generation")
        else:
            self.model = None
            logger.warning("No Gemini API key provided, SEO generation will be limited")

    def generate_seo_content(
        self,
        original_title: str,
        original_description: str = "",
        channel_name: str = "",
        video_url: str = "",
    ) -> dict:
        """
        Generate SEO-optimized content for a trailer video.
        
        Args:
            original_title: Original video title
            original_description: Original video description
            channel_name: Source channel name
            video_url: Original video URL
            
        Returns:
            Dict with 'title', 'description', and 'tags'
        """
        if not self.model:
            logger.warning("Gemini not available, generating basic SEO content")
            return self._generate_basic_seo(original_title)

        try:
            prompt = f"""Generate YouTube SEO metadata for this trailer:

Original Title: {original_title}
Source Channel: {channel_name}
Original Description: {original_description[:500]}

Create an optimized title, description, and tags for re-uploading this trailer.
Make the title unique and catchy while keeping the movie name and trailer type.
The description should be engaging and include relevant keywords and hashtags."""

            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.8,
                    max_output_tokens=1000,
                )
            )

            # Parse the JSON response
            import json
            import re

            text = response.text.strip()
            
            # Try to extract JSON from the response
            # Sometimes Gemini wraps it in markdown code blocks
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
            if json_match:
                text = json_match.group(1).strip()
            
            # Remove any leading/trailing non-JSON characters
            text = text.strip()
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            result = json.loads(text)

            # Validate the result
            if not all(k in result for k in ["title", "description", "tags"]):
                raise ValueError("Missing required fields in AI response")

            logger.info(f"Generated SEO: {result['title']}")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return self._generate_basic_seo(original_title)
        except Exception as e:
            logger.error(f"Error generating SEO content: {e}")
            return self._generate_basic_seo(original_title)

    def _generate_basic_seo(self, original_title: str) -> dict:
        """
        Generate basic SEO content without AI.
        Fallback when Gemini is unavailable.
        """
        # Clean up the title
        title = original_title
        
        # Add channel suffix to make it unique
        if "official" not in title.lower():
            title = f"{title} - Official"
        
        # Basic description template
        description = f"""{title}

Watch the latest trailer! Don't forget to LIKE, SHARE and SUBSCRIBE for more amazing trailers!

#Trailer #{self._extract_movie_name(title)} #Movies #ComingSoon"""

        # Basic tags
        movie_name = self._extract_movie_name(title)
        tags = [
            "trailer", "official trailer", "movie trailer",
            movie_name, f"{movie_name} trailer",
            "new trailer", "coming soon", "2024", "2025",
            "movie", "film", "cinema"
        ]

        # Remove empty tags
        tags = [t for t in tags if t.strip()]

        return {
            "title": title[:100],
            "description": description,
            "tags": tags
        }

    def _extract_movie_name(self, title: str) -> str:
        """Extract movie name from trailer title."""
        import re
        # Remove common trailer suffixes
        name = re.sub(
            r'\s*(official\s+)?(trailer|teaser|preview|first\s+look)\s*(\d+)?$',
            '',
            title,
            flags=re.IGNORECASE
        )
        # Remove year if present
        name = re.sub(r'\s*\(\d{4}\)\s*$', '', name)
        # Remove trailing punctuation
        name = name.strip(' :-')
        return name if name else title[:30]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generator = SEOGenerator()
    result = generator.generate_seo_content(
        "Marvel Studios' Thunderbolts* | Official Trailer",
        "Marvel Studios' Thunderbolts* - Only in theaters May 2025",
        "Marvel Entertainment"
    )
    print(f"Title: {result['title']}")
    print(f"Description: {result['description'][:200]}...")
    print(f"Tags: {result['tags']}")

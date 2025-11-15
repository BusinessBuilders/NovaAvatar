"""
Dialogue Generation Service for Multi-Avatar Conversations.

Generates natural conversations between multiple avatars using GPT-4.
"""

import json
from typing import List, Dict, Optional
from loguru import logger
from openai import AsyncOpenAI
import os

from pydantic import BaseModel


class AvatarPersona(BaseModel):
    """Avatar persona for dialogue generation."""
    name: str
    personality: str
    voice_style: Optional[str] = None


class DialogueExchange(BaseModel):
    """Single exchange in a conversation."""
    avatar_name: str
    text: str
    sequence: int


class GeneratedDialogue(BaseModel):
    """Complete generated dialogue."""
    title: str
    exchanges: List[DialogueExchange]
    total_duration_estimate: float


class DialogueGenerator:
    """Generate dialogue for multi-avatar conversations."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize dialogue generator.

        Args:
            api_key: OpenAI API key (or use OPENAI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required for dialogue generation")

        self.client = AsyncOpenAI(api_key=self.api_key)
        logger.info("Dialogue generator initialized")

    async def generate_conversation(
        self,
        topic: str,
        avatars: List[AvatarPersona],
        num_exchanges: int = 3,
        style: str = "discussion",
        context: Optional[str] = None
    ) -> GeneratedDialogue:
        """
        Generate a multi-avatar conversation.

        Args:
            topic: Topic of conversation
            avatars: List of avatar personas
            num_exchanges: Number of back-and-forth exchanges
            style: Conversation style (discussion, debate, interview, educational)
            context: Additional context for the conversation

        Returns:
            Generated dialogue with all exchanges

        Example:
            >>> avatars = [
            ...     AvatarPersona(name="Alice", personality="Expert AI researcher, enthusiastic"),
            ...     AvatarPersona(name="Bob", personality="Skeptical journalist, asks tough questions")
            ... ]
            >>> dialogue = await generator.generate_conversation(
            ...     topic="The Future of AI",
            ...     avatars=avatars,
            ...     num_exchanges=3,
            ...     style="interview"
            ... )
        """
        logger.info(f"Generating {num_exchanges} exchanges for {len(avatars)} avatars on '{topic}'")

        # Build prompt for GPT-4
        prompt = self._build_dialogue_prompt(topic, avatars, num_exchanges, style, context)

        # Call GPT-4
        response = await self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert dialogue writer who creates engaging, natural conversations between multiple speakers. Generate dialogue in JSON format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.8,  # Higher temperature for more natural dialogue
            response_format={"type": "json_object"}
        )

        # Parse response
        content = response.choices[0].message.content
        dialogue_data = json.loads(content)

        # Convert to DialogueExchange objects
        exchanges = []
        for i, exchange in enumerate(dialogue_data.get("exchanges", [])):
            exchanges.append(DialogueExchange(
                avatar_name=exchange["avatar"],
                text=exchange["text"],
                sequence=i
            ))

        # Estimate total duration (rough: 150 words per minute average speaking)
        total_words = sum(len(ex.text.split()) for ex in exchanges)
        duration_estimate = (total_words / 150) * 60  # seconds

        dialogue = GeneratedDialogue(
            title=dialogue_data.get("title", topic),
            exchanges=exchanges,
            total_duration_estimate=duration_estimate
        )

        logger.info(f"Generated dialogue with {len(exchanges)} exchanges (~{duration_estimate:.1f}s)")
        return dialogue

    def _build_dialogue_prompt(
        self,
        topic: str,
        avatars: List[AvatarPersona],
        num_exchanges: int,
        style: str,
        context: Optional[str]
    ) -> str:
        """Build the prompt for dialogue generation."""

        # Avatar descriptions
        avatar_desc = "\n".join([
            f"- {a.name}: {a.personality}"
            for a in avatars
        ])

        # Style-specific instructions
        style_instructions = {
            "discussion": "Create a balanced discussion where all participants contribute equally and build on each other's points.",
            "debate": "Create a debate with opposing viewpoints. Participants should challenge each other's arguments respectfully but firmly.",
            "interview": f"Create an interview where {avatars[0].name} asks questions and the others respond. Make it engaging and informative.",
            "educational": "Create an educational dialogue where participants explain concepts clearly and ask clarifying questions.",
            "panel": "Create a panel discussion where each participant offers unique perspectives on the topic."
        }

        style_instruction = style_instructions.get(style, style_instructions["discussion"])

        # Build prompt
        prompt = f"""Generate a natural, engaging conversation between {len(avatars)} avatars on the topic: "{topic}"

**Avatars:**
{avatar_desc}

**Style:** {style}
{style_instruction}

**Requirements:**
- Generate exactly {num_exchanges} exchanges total (each avatar should speak multiple times)
- Each exchange should be 2-4 sentences
- Make the dialogue natural and conversational
- Include relevant questions, insights, and reactions
- Ensure smooth transitions between speakers
- Keep it engaging and informative

{f'**Additional Context:**\n{context}\n' if context else ''}

**Output Format (JSON):**
{{
    "title": "Engaging title for this conversation",
    "exchanges": [
        {{"avatar": "Avatar Name", "text": "What they say..."}},
        {{"avatar": "Avatar Name", "text": "Response..."}},
        ...
    ]
}}

Generate the conversation now:"""

        return prompt

    async def generate_followup(
        self,
        previous_exchanges: List[DialogueExchange],
        avatars: List[AvatarPersona],
        num_additional: int = 1
    ) -> List[DialogueExchange]:
        """
        Generate followup exchanges to extend a conversation.

        Args:
            previous_exchanges: Previous dialogue exchanges
            avatars: Avatar personas
            num_additional: Number of additional exchanges to generate

        Returns:
            List of new dialogue exchanges
        """
        # Convert previous to text
        prev_text = "\n".join([
            f"{ex.avatar_name}: {ex.text}"
            for ex in previous_exchanges
        ])

        prompt = f"""Continue the following conversation with {num_additional} more natural exchanges:

{prev_text}

**Avatars:**
{chr(10).join([f"- {a.name}: {a.personality}" for a in avatars])}

Generate {num_additional} more exchanges that naturally continue this conversation.

Output in JSON format:
{{
    "exchanges": [
        {{"avatar": "Name", "text": "..."}},
        ...
    ]
}}"""

        response = await self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You continue conversations naturally. Generate dialogue in JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        # Create new exchanges with updated sequence numbers
        start_seq = len(previous_exchanges)
        new_exchanges = []
        for i, exchange in enumerate(data.get("exchanges", [])):
            new_exchanges.append(DialogueExchange(
                avatar_name=exchange["avatar"],
                text=exchange["text"],
                sequence=start_seq + i
            ))

        return new_exchanges


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        generator = DialogueGenerator()

        # Create avatar personas
        avatars = [
            AvatarPersona(
                name="Dr. Sarah Chen",
                personality="AI safety researcher, thoughtful and cautious about AI development"
            ),
            AvatarPersona(
                name="Marcus Williams",
                personality="Tech entrepreneur, optimistic about AI's potential"
            ),
            AvatarPersona(
                name="Prof. Lisa Johnson",
                personality="Ethics professor, focuses on societal implications"
            )
        ]

        # Generate conversation
        dialogue = await generator.generate_conversation(
            topic="The Impact of AI on Employment",
            avatars=avatars,
            num_exchanges=6,
            style="panel",
            context="Focus on both opportunities and challenges"
        )

        print(f"\n=== {dialogue.title} ===\n")
        for exchange in dialogue.exchanges:
            print(f"{exchange.avatar_name}: {exchange.text}\n")

        print(f"\nEstimated duration: {dialogue.total_duration_estimate:.1f}s")

    asyncio.run(main())

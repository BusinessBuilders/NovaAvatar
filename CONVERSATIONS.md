
# Multi-Avatar Conversations

Create engaging conversations between multiple AI avatars discussing any topic.

## Overview

NovaAvatar's conversation feature allows you to create videos where multiple avatars discuss topics naturally, like a panel discussion, debate, or interview.

**Features:**
- 🗣️ Multiple avatars with unique personalities
- 🤖 AI-generated dialogue using GPT-4
- 🎬 Automatic video generation for each speaker
- ✂️ Smart video stitching with transitions
- 🎨 Customizable conversation styles

## Quick Start

### 1. Create Avatar Profiles

First, create avatar profiles with distinct personalities:

```python
from examples.python.multi_avatar_conversation import ConversationClient

client = ConversationClient(api_key="your_api_key")

# Create first avatar
alice = client.create_avatar(
    name="Dr. Alice Chen",
    personality="Enthusiastic AI researcher, optimistic about technology",
    image_path="avatars/alice.png"
)

# Create second avatar
bob = client.create_avatar(
    name="Bob Martinez",
    personality="Skeptical journalist, asks tough questions",
    image_path="avatars/bob.png"
)
```

### 2. Create a Conversation

```python
conversation = client.create_conversation(
    title="The Future of AI",
    topic="How will AI change our lives in the next decade?",
    avatar_ids=[alice['id'], bob['id']],
    num_exchanges=6,
    style="discussion"
)

print(f"Video: {conversation['final_video_path']}")
```

## Conversation Styles

### Discussion (Balanced)
All participants contribute equally, building on each other's points.

```python
style="discussion"
```

**Best for:** Panel discussions, roundtables

### Debate (Opposing Views)
Participants take opposing sides and challenge each other's arguments.

```python
style="debate"
```

**Best for:** Controversial topics, pro/con discussions

### Interview (Q&A)
First avatar asks questions, others respond.

```python
style="interview"
```

**Best for:** Expert interviews, educational content

### Panel (Unique Perspectives)
Each participant offers their unique viewpoint.

```python
style="panel"
```

**Best for:** Multi-expert discussions, diverse perspectives

## Avatar Personalities

The personality field determines how the avatar speaks and what perspectives they bring.

### Good Personality Examples

**Expert:**
```python
personality="PhD in machine learning, speaks technically but clearly"
```

**Enthusiast:**
```python
personality="Tech enthusiast who gets excited about new innovations"
```

**Skeptic:**
```python
personality="Critical thinker who questions claims and asks for evidence"
```

**Educator:**
```python
personality="Patient teacher who explains complex topics simply"
```

**Philosopher:**
```python
personality="Deep thinker who considers ethical and philosophical implications"
```

## API Reference

### Create Avatar Profile

```http
POST /api/conversations/avatars
```

**Request:**
```json
{
  "name": "Dr. Sarah Chen",
  "personality": "AI researcher, enthusiastic",
  "description": "Expert in neural networks",
  "image_path": "avatars/sarah.png",
  "voice_style": "professional, calm"
}
```

**Response:**
```json
{
  "id": "uuid-here",
  "name": "Dr. Sarah Chen",
  "personality": "AI researcher, enthusiastic",
  "is_active": true
}
```

### Create Conversation

```http
POST /api/conversations
```

**Request:**
```json
{
  "title": "AI Ethics Discussion",
  "topic": "Should we develop AGI?",
  "avatar_ids": ["uuid1", "uuid2", "uuid3"],
  "num_exchanges": 6,
  "style": "panel",
  "stitch_videos": true,
  "add_transitions": true
}
```

**Response:**
```json
{
  "conversation_id": "uuid",
  "title": "AI Ethics Discussion",
  "status": "generating",
  "progress": 0
}
```

### Get Conversation Status

```http
GET /api/conversations/{conversation_id}
```

**Response:**
```json
{
  "conversation_id": "uuid",
  "status": "completed",
  "progress": 100,
  "final_video_path": "storage/conversations/conversation_uuid.mp4"
}
```

### Get Dialogue

```http
GET /api/conversations/{conversation_id}/dialogue
```

**Response:**
```json
[
  {
    "sequence": 0,
    "avatar_name": "Alice",
    "text": "I believe AI will revolutionize healthcare...",
    "video_path": "storage/conversations/line_0.mp4"
  },
  {
    "sequence": 1,
    "avatar_name": "Bob",
    "text": "But what about the risks?...",
    "video_path": "storage/conversations/line_1.mp4"
  }
]
```

## Advanced Usage

### Custom Context

Provide additional context to guide the conversation:

```python
conversation = client.create_conversation(
    title="Climate Tech Discussion",
    topic="How can technology help fight climate change?",
    avatar_ids=[alice_id, bob_id],
    context="""
    Focus on practical solutions that are available today.
    Discuss both renewable energy and carbon capture.
    Keep explanations accessible to general audiences.
    """
)
```

### Split-Screen Layout

Instead of sequential dialogue, show avatars side-by-side:

```python
# This feature is available via the VideoStitcher service
from services.video_stitcher import VideoStitcher

stitcher = VideoStitcher()
result = stitcher.create_split_screen(
    segments=[video1, video2],
    output_name="split_screen",
    layout="horizontal"  # or "vertical", "grid"
)
```

## Examples

### Example 1: Tech Panel

```python
# 3 avatars discussing tech trends
avatars = [
    create_avatar("Alice", "Optimistic futurist"),
    create_avatar("Bob", "Practical engineer"),
    create_avatar("Carol", "Privacy advocate")
]

conversation = create_conversation(
    title="Tech Trends 2024",
    topic="What technology will define 2024?",
    avatar_ids=avatar_ids,
    num_exchanges=9,  # 3 each
    style="panel"
)
```

### Example 2: Educational Interview

```python
# Teacher avatar interviewing expert
teacher = create_avatar("Ms. Johnson", "Patient educator")
expert = create_avatar("Dr. Smith", "Climate scientist")

conversation = create_conversation(
    title="Climate Science 101",
    topic="Explain climate change in simple terms",
    avatar_ids=[teacher_id, expert_id],
    style="interview"
)
```

### Example 3: Debate

```python
# Two opposing viewpoints
pro = create_avatar("Alex", "Supports regulation")
con = create_avatar("Jordan", "Opposes regulation")

conversation = create_conversation(
    title="AI Regulation Debate",
    topic="Should AI be heavily regulated?",
    avatar_ids=[pro_id, con_id],
    num_exchanges=8,
    style="debate"
)
```

## Tips for Best Results

### Personality Writing

**Good:**
- "Enthusiastic researcher who simplifies complex topics"
- "Skeptical analyst who questions assumptions"
- "Philosophical thinker who considers ethics"

**Avoid:**
- Too vague: "Nice person"
- Too long: Full paragraphs
- Contradictory: "Quiet but very talkative"

### Number of Exchanges

- **2-3 exchanges:** Quick back-and-forth
- **4-6 exchanges:** Standard conversation
- **8-12 exchanges:** In-depth discussion
- **More than 12:** Very long, may lose coherence

### Avatar Count

- **2 avatars:** Great for interviews, debates
- **3 avatars:** Ideal for panels, diverse views
- **4+ avatars:** Possible but harder to manage

## Performance

**Generation Time:**
- Dialogue: ~10-30 seconds (GPT-4)
- Audio per line: ~5 seconds (TTS)
- Video per line: ~2-5 minutes (OmniAvatar)
- Stitching: ~10-30 seconds

**Total:** ~5-10 minutes per exchange

**Example:** 6-exchange conversation with 3 avatars = ~30-60 minutes total

## Troubleshooting

### Avatars repeating points

- Give avatars more distinct personalities
- Add context to guide unique perspectives
- Increase num_exchanges for more depth

### Unnatural dialogue

- Use appropriate conversation style
- Provide better topic description
- Add context about tone/audience

### Video stitching fails

- Check that all individual videos generated successfully
- Ensure ffmpeg is installed
- Try with `add_transitions=False`

## API Examples in Other Languages

### JavaScript

```javascript
const response = await fetch('http://localhost:8000/api/conversations', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your_api_key'
  },
  body: JSON.stringify({
    title: "AI Discussion",
    topic: "The future of work",
    avatar_ids: [alice_id, bob_id],
    num_exchanges: 4,
    style: "discussion"
  })
});

const conversation = await response.json();
console.log(conversation.conversation_id);
```

### cURL

```bash
curl -X POST http://localhost:8000/api/conversations \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{
    "title": "Tech Talk",
    "topic": "Quantum computing explained",
    "avatar_ids": ["uuid1", "uuid2"],
    "num_exchanges": 4,
    "style": "interview"
  }'
```

## Resources

- [API Documentation](http://localhost:8000/docs)
- [Example Scripts](examples/python/)
- [Video Stitching Guide](services/video_stitcher.py)
- [Dialogue Generation](services/dialogue_generator.py)

---

**Ready to create engaging conversations?** Start by creating your avatar profiles and let NovaAvatar handle the rest!

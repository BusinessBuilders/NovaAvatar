# NovaAvatar Architecture

Complete automated avatar video generation system with content scraping, AI script generation, and production workflows.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         NovaAvatar Pipeline                      │
└─────────────────────────────────────────────────────────────────┘

1. Content Scraping (RSS, Reddit, NewsAPI)
           ↓
2. Script Generation (OpenAI GPT-4)
           ↓
3. Background Generation (Flux via Replicate)
           ↓
4. Audio Generation (Dia TTS or OpenAI TTS)
           ↓
5. Avatar Video Generation (OmniAvatar)
           ↓
6. Review Queue → Approval → Export
```

## Directory Structure

```
NovaAvatar/
├── api/                      # FastAPI REST API
│   ├── __init__.py
│   └── server.py            # API endpoints
│
├── frontend/                 # Gradio Web UI
│   └── app.py               # Web interface
│
├── services/                 # Core business logic
│   ├── __init__.py
│   ├── content_scraper.py   # RSS, Reddit, NewsAPI scraping
│   ├── script_generator.py  # GPT-4 script generation
│   ├── image_generator.py   # Flux background generation
│   ├── tts_service.py       # Dia/OpenAI TTS
│   ├── avatar_service.py    # OmniAvatar wrapper
│   └── orchestrator.py      # Pipeline coordinator
│
├── config/                   # Configuration
│   └── settings.py          # Pydantic settings management
│
├── storage/                  # Generated content (gitignored)
│   ├── uploads/             # User uploads
│   ├── generated/           # Generated images/audio
│   ├── videos/              # Final videos
│   └── queue/               # Review queue
│
├── OmniAvatar/              # Original OmniAvatar code
├── configs/                 # Model configurations
├── scripts/                 # Inference scripts
├── pretrained_models/       # Model files (gitignored)
│
├── .env.example             # Environment template
├── .gitignore               # Git exclusions
├── requirements.txt         # Python dependencies
├── run.py                   # Launcher script
├── SETUP.md                 # Setup guide
├── ARCHITECTURE.md          # This file
└── README.md                # Project overview
```

## Components

### 1. Content Scraper (`services/content_scraper.py`)

**Purpose:** Scrape trending content from multiple sources

**Sources:**
- RSS Feeds (CNN, BBC, NPR, NYTimes, TechCrunch)
- Reddit (via PRAW)
- NewsAPI (free tier: 100 req/day)

**Features:**
- Async scraping
- Deduplication
- Relevance scoring
- Configurable sources

**Output:** List of `ContentItem` objects with title, description, source, URL

### 2. Script Generator (`services/script_generator.py`)

**Purpose:** Generate video scripts from content using GPT-4

**Features:**
- Multiple styles (news anchor, casual, educational, etc.)
- Duration control (15-90 seconds)
- Scene description generation (for image gen)
- Keyword extraction
- Call-to-action support

**Output:** `VideoScript` with script text, scene description, duration estimate

### 3. Image Generator (`services/image_generator.py`)

**Purpose:** Generate background images using Flux

**Model:** Flux Schnell (fast) or Flux Dev (quality) via Replicate

**Features:**
- Photorealistic backgrounds
- Multiple style options
- Aspect ratio control
- Batch generation
- Default background fallback

**Output:** `GeneratedImage` with path, prompt, metadata

### 4. TTS Service (`services/tts_service.py`)

**Purpose:** Convert text to speech

**Backends:**
- **Dia TTS** (preferred, local, free)
- **OpenAI TTS** (fallback, API-based)

**Features:**
- 16kHz output (OmniAvatar requirement)
- Voice selection
- Speed control
- Automatic format conversion
- Fallback mechanism

**Output:** `GeneratedAudio` with path, duration, sample rate

### 5. Avatar Service (`services/avatar_service.py`)

**Purpose:** Wrapper for OmniAvatar video generation

**Features:**
- Lazy loading (don't load models until needed)
- VRAM management
- TeaCache acceleration
- Progress callbacks
- Parameter customization
- Error recovery

**Models:**
- 14B model (higher quality, 21-36GB VRAM)
- 1.3B model (faster, 12GB VRAM)

**Output:** `AvatarVideo` with path, duration, metadata

### 6. Orchestrator (`services/orchestrator.py`)

**Purpose:** Coordinate the full pipeline

**Features:**
- End-to-end automation
- Job tracking
- Status management
- Review queue
- Batch processing
- Error handling
- Redis queue integration (optional)

**Workflow:**
```python
content → script → image → audio → video → queue → approve
```

## User Interfaces

### Gradio Web UI (`frontend/app.py`)

**Features:**
- Dashboard with stats
- Content scraper interface
- Manual video creation
- Review queue with approval
- Settings configuration

**Access:** http://localhost:7860

### FastAPI REST API (`api/server.py`)

**Endpoints:**
- `POST /api/scrape` - Scrape content
- `POST /api/generate` - Generate video
- `GET /api/jobs` - List jobs
- `GET /api/jobs/{id}` - Job status
- `GET /api/queue` - Review queue
- `POST /api/queue/{id}/approve` - Approve video
- `GET /api/videos/{id}` - Download video

**Access:** http://localhost:8000
**Docs:** http://localhost:8000/docs

## Configuration

### Environment Variables (`.env`)

**Required:**
- `OPENAI_API_KEY` - GPT-4 script generation
- `REPLICATE_API_TOKEN` - Flux image generation

**Optional:**
- `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` - Reddit scraping
- `NEWSAPI_KEY` - News scraping
- `DIA_MODEL_PATH` - Local TTS model

**Model:**
- `USE_14B_MODEL` - true/false

**Generation:**
- `NUM_STEPS` - Inference steps (10-50)
- `GUIDANCE_SCALE` - CFG scale (1-10)
- `TEA_CACHE_THRESH` - Acceleration (0-0.15)
- `ENABLE_VRAM_MANAGEMENT` - true/false

### Settings Management (`config/settings.py`)

**Features:**
- Pydantic validation
- Type safety
- Environment variable loading
- Settings validation
- Logging configuration
- Sentry integration

## Data Flow

### Automated Pipeline

```
1. User clicks "Scrape Content"
   └─> ContentScraper fetches from RSS/Reddit/News
   └─> Returns 10-20 items

2. User selects items and clicks "Generate"
   └─> For each item:
       ├─> ScriptGenerator (GPT-4) → script + scene description
       ├─> ImageGenerator (Flux) → background.jpg
       ├─> TTSService (Dia/OpenAI) → audio.wav
       └─> AvatarService (OmniAvatar) → video.mp4

3. Videos go to Review Queue
   └─> User previews and approves
   └─> Approved videos marked as complete
```

### Manual Creation

```
1. User uploads image + audio OR generates via TTS
2. User writes prompt
3. AvatarService generates video
4. Video saved and ready for export
```

## Production Features

### Logging
- Structured logging with loguru
- File rotation (1 day, 7 day retention)
- Log levels (DEBUG, INFO, WARNING, ERROR)
- Sentry integration for error tracking

### Error Handling
- Graceful degradation (TTS fallback)
- Retry logic
- Detailed error messages
- Status tracking

### Performance
- Async operations
- Lazy loading
- VRAM optimization
- TeaCache acceleration
- GPU memory management

### Security
- API key management via .env
- CORS configuration
- File upload validation
- Path sanitization

## Scaling Considerations

### Single Machine
- Use 1.3B model for speed
- Enable TeaCache
- VRAM management
- Sequential processing

### Multi-GPU
- Sequence parallelism (sp_size)
- FSDP for larger models
- Parallel job processing

### Production
- Redis job queue
- Worker processes
- Load balancing
- CDN for videos
- Object storage (S3)

## API Integration

### Example: Create Video from Content

```python
import requests

response = requests.post('http://localhost:8000/api/generate', json={
    "content_title": "AI Breakthrough",
    "content_description": "New AI achieves human-level performance...",
    "style": "professional",
    "duration": 45
})

job = response.json()
job_id = job['job_id']

# Poll for completion
status = requests.get(f'http://localhost:8000/api/jobs/{job_id}').json()

# Download video
video = requests.get(f'http://localhost:8000/api/videos/{job_id}')
with open('video.mp4', 'wb') as f:
    f.write(video.content)
```

## Future Enhancements

- [ ] Voice cloning for consistent avatar voice
- [ ] Multi-language support
- [ ] Social media auto-posting
- [ ] Scheduled content generation
- [ ] Custom avatar training
- [ ] Video editing capabilities
- [ ] Analytics and metrics
- [ ] A/B testing for prompts
- [ ] Video templating system
- [ ] Batch export features

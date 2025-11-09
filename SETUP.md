# NovaAvatar Setup Guide

Complete setup guide for the NovaAvatar automated avatar video generation system.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Model Download](#model-download)
4. [Configuration](#configuration)
5. [Running the Application](#running-the-application)
6. [API Usage](#api-usage)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

**GPU Requirements:**
- NVIDIA GPU with CUDA support
- 14B Model: 21-36GB VRAM (RTX 4090, A100, etc.)
- 1.3B Model: 12GB VRAM (RTX 3090, 4080, etc.)

**Software:**
- Python 3.10 or higher
- CUDA 12.4 or compatible
- FFmpeg (for audio/video processing)
- Redis (optional, for job queue)

**Operating System:**
- Linux (recommended)
- Windows with WSL2
- macOS (limited GPU support)

### API Keys Required

1. **OpenAI API Key** (required)
   - Get from: https://platform.openai.com/api-keys
   - Used for: GPT-4 script generation

2. **Replicate API Token** (required)
   - Get from: https://replicate.com/account/api-tokens
   - Used for: Flux image generation

3. **Optional APIs:**
   - Reddit API credentials (for Reddit content scraping)
   - NewsAPI key (for news scraping)

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/BusinessBuilders/NovaAvatar.git
cd NovaAvatar
```

### 2. Create Virtual Environment

```bash
python -m venv omniavatar_env
source omniavatar_env/bin/activate  # Linux/Mac
# OR
omniavatar_env\Scripts\activate  # Windows
```

### 3. Install PyTorch with CUDA

```bash
pip install torch==2.4.0 torchvision==0.19.0 torchaudio==2.4.0 --index-url https://download.pytorch.org/whl/cu124
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Install Optional Components

**Flash Attention (recommended for speed):**
```bash
pip install flash_attn
```

**Dia TTS (local TTS, free alternative to OpenAI TTS):**
```bash
# Follow instructions at: https://github.com/nari-labs/dia/
```

**Redis (for production job queue):**
```bash
# Linux
sudo apt-get install redis-server

# macOS
brew install redis

# Start Redis
redis-server
```

---

## Model Download

### Download OmniAvatar Models

Choose either 14B (better quality) or 1.3B (faster) model:

```bash
mkdir pretrained_models
pip install "huggingface_hub[cli]"
```

**For 14B Model (recommended for quality):**
```bash
# Base model
huggingface-cli download Wan-AI/Wan2.1-T2V-14B --local-dir ./pretrained_models/Wan2.1-T2V-14B

# Audio encoder
huggingface-cli download facebook/wav2vec2-base-960h --local-dir ./pretrained_models/wav2vec2-base-960h

# OmniAvatar LoRA
huggingface-cli download OmniAvatar/OmniAvatar-14B --local-dir ./pretrained_models/OmniAvatar-14B
```

**For 1.3B Model (faster, less VRAM):**
```bash
# Base model
huggingface-cli download Wan-AI/Wan2.1-T2V-1.3B --local-dir ./pretrained_models/Wan2.1-T2V-1.3B

# Audio encoder
huggingface-cli download facebook/wav2vec2-base-960h --local-dir ./pretrained_models/wav2vec2-base-960h

# OmniAvatar LoRA
huggingface-cli download OmniAvatar/OmniAvatar-1.3B --local-dir ./pretrained_models/OmniAvatar-1.3B
```

**Optional: CLIP Image Encoder (for dynamic backgrounds):**
```bash
huggingface-cli download calcuis/wan-gguf clip_vision_h.safetensors --local-dir ./pretrained_models/clip_vision_h
```

---

## Configuration

### 1. Create Environment File

```bash
cp .env.example .env
```

### 2. Edit `.env` File

Open `.env` and configure:

**Required Settings:**
```bash
# AI Services
OPENAI_API_KEY=sk-your-key-here
REPLICATE_API_TOKEN=r8_your-token-here

# Model Selection (true for 14B, false for 1.3B)
USE_14B_MODEL=false
```

**Optional Content Sources:**
```bash
# Reddit
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret

# News API
NEWSAPI_KEY=your_newsapi_key
```

**Performance Tuning:**
```bash
# Inference steps (higher = better quality, slower)
NUM_STEPS=25

# Guidance scale (4-6 recommended)
GUIDANCE_SCALE=4.5

# TeaCache threshold (0.14 for 2-3x speedup)
TEA_CACHE_THRESH=0.14

# VRAM management (true to save memory)
ENABLE_VRAM_MANAGEMENT=true
```

### 3. Validate Configuration

```bash
python config/settings.py
```

This will check that:
- Required API keys are set
- Model files are downloaded
- Paths are configured correctly

---

## Running the Application

### Option 1: Gradio Web UI (Recommended)

**Start the web interface:**
```bash
python frontend/app.py
```

**Access at:** http://localhost:7860

**Features:**
- Dashboard with job overview
- Content scraper (RSS, Reddit, News)
- Manual video creation
- Review queue for approval
- Settings configuration

### Option 2: FastAPI Server

**Start the API server:**
```bash
python api/server.py
```

**Access at:** http://localhost:8000

**API Documentation:** http://localhost:8000/docs

### Option 3: Both (Production)

**Terminal 1 - API Server:**
```bash
uvicorn api.server:app --host 0.0.0.0 --port 8000
```

**Terminal 2 - Gradio UI:**
```bash
python frontend/app.py
```

**Terminal 3 - Redis (if using job queue):**
```bash
redis-server
```

---

## API Usage

### Scrape Content

```bash
curl -X POST http://localhost:8000/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"max_items": 5}'
```

### Generate Video

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "content_title": "AI Breakthrough",
    "content_description": "New AI system achieves 95% accuracy...",
    "style": "professional",
    "duration": 45
  }'
```

### Check Job Status

```bash
curl http://localhost:8000/api/jobs/{job_id}
```

### Download Video

```bash
curl http://localhost:8000/api/videos/{job_id} -o video.mp4
```

---

## Full Pipeline Example

### Automated Content Pipeline

1. **Scrape Content**
   ```python
   from services.orchestrator import PipelineOrchestrator

   orchestrator = PipelineOrchestrator()
   items = await orchestrator.scrape_content(max_items=10)
   ```

2. **Generate Videos**
   ```python
   for item in items[:3]:  # Process first 3
       job = await orchestrator.create_video_from_content(
           item,
           style=ScriptStyle.PROFESSIONAL,
           duration=45
       )
       print(f"Video: {job.video_file}")
   ```

3. **Review Queue**
   ```python
   queue = orchestrator.get_review_queue()
   for job in queue:
       orchestrator.approve_video(job.job_id)
   ```

### Manual Creation

```python
from services.avatar_service import AvatarService

service = AvatarService(use_14b_model=False)

video = await service.generate_video(
    prompt="Professional woman in modern office",
    image_path="my_image.jpg",
    audio_path="my_audio.wav"
)

print(f"Generated: {video.video_path}")
```

---

## Troubleshooting

### CUDA Out of Memory

**Solutions:**
1. Use 1.3B model instead of 14B
2. Enable VRAM management: `ENABLE_VRAM_MANAGEMENT=true`
3. Reduce inference steps: `NUM_STEPS=20`
4. Reduce persistent params in config:
   ```yaml
   num_persistent_param_in_dit: 0
   ```

### Slow Generation

**Solutions:**
1. Enable TeaCache: `TEA_CACHE_THRESH=0.14`
2. Install Flash Attention: `pip install flash_attn`
3. Use fewer inference steps: `NUM_STEPS=20`
4. Use multi-GPU with sequence parallelism

### API Key Errors

**Check:**
1. `.env` file exists and has correct keys
2. No extra spaces in API keys
3. Keys are not expired
4. Environment variables are loaded

### Model Not Found

**Solutions:**
1. Re-download models:
   ```bash
   huggingface-cli download Wan-AI/Wan2.1-T2V-1.3B --local-dir ./pretrained_models/Wan2.1-T2V-1.3B
   ```
2. Check paths in configs:
   ```bash
   ls pretrained_models/
   ```

### Redis Connection Failed

**Solutions:**
1. Start Redis: `redis-server`
2. Check Redis URL in `.env`
3. Or disable queue: Set `enable_queue=False` in orchestrator

---

## Performance Optimization

### Speed vs Quality Trade-offs

| Setting | Speed | Quality | VRAM |
|---------|-------|---------|------|
| num_steps=20, tea_cache=0.15 | Fast | Good | Low |
| num_steps=30, tea_cache=0.10 | Medium | Better | Medium |
| num_steps=50, tea_cache=0 | Slow | Best | High |

### Recommended Configurations

**Fast (Good for testing):**
```bash
NUM_STEPS=20
TEA_CACHE_THRESH=0.15
ENABLE_VRAM_MANAGEMENT=true
USE_14B_MODEL=false
```

**Balanced (Recommended):**
```bash
NUM_STEPS=25
TEA_CACHE_THRESH=0.14
ENABLE_VRAM_MANAGEMENT=true
USE_14B_MODEL=false
```

**Quality (Best results):**
```bash
NUM_STEPS=50
TEA_CACHE_THRESH=0
ENABLE_VRAM_MANAGEMENT=false
USE_14B_MODEL=true
```

---

## Next Steps

1. **Test the pipeline:**
   - Run the Gradio UI
   - Scrape some content
   - Generate a test video

2. **Customize:**
   - Adjust generation parameters
   - Create custom prompts
   - Add your own default backgrounds

3. **Production deployment:**
   - Set up Redis for job queue
   - Configure Nginx reverse proxy
   - Enable monitoring with Sentry
   - Set up automated scraping schedule

4. **Integrate:**
   - Connect to your CMS
   - Add social media publishing
   - Build custom workflows

---

## Support

- GitHub Issues: https://github.com/BusinessBuilders/NovaAvatar/issues
- Original OmniAvatar: https://github.com/Omni-Avatar/OmniAvatar
- Dia TTS: https://github.com/nari-labs/dia/

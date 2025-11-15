# NovaAvatar

[![Tests](https://github.com/BusinessBuilders/NovaAvatar/workflows/Tests/badge.svg)](https://github.com/BusinessBuilders/NovaAvatar/actions/workflows/test.yml)
[![Lint](https://github.com/BusinessBuilders/NovaAvatar/workflows/Lint/badge.svg)](https://github.com/BusinessBuilders/NovaAvatar/actions/workflows/lint.yml)
[![codecov](https://codecov.io/gh/BusinessBuilders/NovaAvatar/branch/main/graph/badge.svg)](https://codecov.io/gh/BusinessBuilders/NovaAvatar)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE.txt)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**Automated avatar video generation with AI-powered content pipeline**

Built on [OmniAvatar](https://github.com/Omni-Avatar/OmniAvatar) - adds automated content scraping, script generation, and production workflow.

---

## 🚀 What's New in NovaAvatar

**Complete Content-to-Video Automation:**
1. 📰 **Auto-scrape trending content** from RSS, Reddit, NewsAPI
2. 🤖 **AI-generated scripts** using OpenAI GPT-4
3. 🎨 **Dynamic backgrounds** via Flux API
4. 🗣️ **Text-to-speech** with Dia TTS or OpenAI
5. 🎬 **Avatar videos** with OmniAvatar
6. ✅ **Review queue** for approval workflow

**NEW: Multi-Avatar Conversations 🗣️🗣️🗣️**
- Create engaging conversations between multiple avatars
- AI-generated dialogue with unique personalities
- Automatic video stitching with transitions
- Panel discussions, debates, interviews, and more
- [Learn more →](CONVERSATIONS.md)

**Two interfaces:**
- 🖥️ **Gradio Web UI** - Visual dashboard (port 7860)
- 🔌 **REST API** - Programmatic access (port 8000)

---

## ⚡ Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/BusinessBuilders/NovaAvatar.git
cd NovaAvatar
python -m venv omniavatar_env
source omniavatar_env/bin/activate  # Linux/Mac
# omniavatar_env\Scripts\activate  # Windows
```

### 2. Install Dependencies

```bash
# PyTorch with CUDA
pip install torch==2.4.0 torchvision==0.19.0 torchaudio==2.4.0 --index-url https://download.pytorch.org/whl/cu124

# All dependencies
pip install -r requirements.txt

# Optional: Flash Attention (2-3x speedup)
pip install flash_attn
```

### 3. Download Models

```bash
mkdir pretrained_models
pip install "huggingface_hub[cli]"

# For 1.3B model (12GB VRAM, recommended)
huggingface-cli download Wan-AI/Wan2.1-T2V-1.3B --local-dir ./pretrained_models/Wan2.1-T2V-1.3B
huggingface-cli download OmniAvatar/OmniAvatar-1.3B --local-dir ./pretrained_models/OmniAvatar-1.3B

# OR for 14B model (21-36GB VRAM, better quality)
huggingface-cli download Wan-AI/Wan2.1-T2V-14B --local-dir ./pretrained_models/Wan2.1-T2V-14B
huggingface-cli download OmniAvatar/OmniAvatar-14B --local-dir ./pretrained_models/OmniAvatar-14B

# Audio encoder (required)
huggingface-cli download facebook/wav2vec2-base-960h --local-dir ./pretrained_models/wav2vec2-base-960h

# Optional: CLIP for dynamic backgrounds
huggingface-cli download calcuis/wan-gguf clip_vision_h.safetensors --local-dir ./pretrained_models/clip_vision_h
```

### 4. Configure API Keys

```bash
cp .env.example .env
nano .env  # or use your editor
```

**Required in `.env`:**
```bash
OPENAI_API_KEY=sk-your-openai-key-here
REPLICATE_API_TOKEN=r8_your-replicate-token-here
USE_14B_MODEL=false  # true for 14B, false for 1.3B
```

**Get API keys:**
- OpenAI: https://platform.openai.com/api-keys
- Replicate: https://replicate.com/account/api-tokens

### 5. Launch!

```bash
# Web UI (recommended for first use)
python run.py

# Or API server
python run.py api

# Check setup
python run.py setup
```

Access the Web UI at: **http://localhost:7860**

---

## 💡 Usage Examples

### Web UI - Automated Pipeline

1. **Open** http://localhost:7860
2. **Click "Content Scraper" tab**
3. **Click "Scrape Content"** - fetches trending topics
4. **Select topics** you want to make videos about
5. **Click "Generate Videos"** - full pipeline runs automatically
6. **Review Queue tab** - preview and approve videos

### API - Programmatic Access

```python
import requests

# Scrape content
response = requests.post('http://localhost:8000/api/scrape',
    json={"max_items": 5})
items = response.json()

# Generate video from content
response = requests.post('http://localhost:8000/api/generate',
    json={
        "content_title": items[0]["title"],
        "content_description": items[0]["description"],
        "style": "professional",
        "duration": 45
    })

job = response.json()
print(f"Job ID: {job['job_id']}")

# Check status
status = requests.get(f'http://localhost:8000/api/jobs/{job["job_id"]}').json()
print(f"Status: {status['status']}")

# Download when complete
video = requests.get(f'http://localhost:8000/api/videos/{job["job_id"]}')
with open('video.mp4', 'wb') as f:
    f.write(video.content)
```

### Manual Creation

```python
from services.avatar_service import AvatarService

service = AvatarService(use_14b_model=False)

video = await service.generate_video(
    prompt="Professional woman speaking about tech in modern office",
    image_path="my_image.jpg",
    audio_path="my_audio.wav"
)

print(f"Video created: {video.video_path}")
```

### CLI - Original OmniAvatar

```bash
# 1.3B model
torchrun --standalone --nproc_per_node=1 scripts/inference.py \
    --config configs/inference_1.3B.yaml \
    --input_file examples/infer_samples.txt

# 14B model
torchrun --standalone --nproc_per_node=1 scripts/inference.py \
    --config configs/inference.yaml \
    --input_file examples/infer_samples.txt
```

**Input format:** `examples/infer_samples.txt`
```
A realistic video of a man speaking...@@examples/images/0000.jpeg@@examples/audios/0000.MP3
```

---

## 📁 Project Structure

```
NovaAvatar/
├── run.py                  # Launcher script ⭐
├── .env.example           # Configuration template
├── SETUP.md               # Detailed setup guide
├── ARCHITECTURE.md        # System architecture docs
│
├── services/              # Core pipeline services
│   ├── content_scraper.py    # RSS, Reddit, NewsAPI
│   ├── script_generator.py   # GPT-4 scripts
│   ├── image_generator.py    # Flux backgrounds
│   ├── tts_service.py        # Dia/OpenAI TTS
│   ├── avatar_service.py     # OmniAvatar wrapper
│   └── orchestrator.py       # Pipeline coordinator
│
├── frontend/              # Gradio Web UI
│   └── app.py
│
├── api/                   # FastAPI REST API
│   └── server.py
│
├── config/                # Settings management
│   └── settings.py
│
├── OmniAvatar/           # Original OmniAvatar code
├── configs/              # Model configurations
├── pretrained_models/    # Downloaded models
└── storage/              # Generated content
    ├── generated/        # Images & audio
    ├── videos/           # Final videos
    └── queue/            # Review queue
```

---

## 🎯 Key Features

### Automated Content Pipeline
- **Content Sources:** RSS feeds, Reddit, NewsAPI
- **Script Generation:** GPT-4 with multiple styles (news, casual, professional)
- **Dynamic Backgrounds:** Flux-generated scenes matching your content
- **Voice Synthesis:** Dia TTS (local/free) or OpenAI TTS
- **Batch Processing:** Generate multiple videos automatically

### Production-Ready
- **Review Queue:** Preview and approve before publishing
- **Job Tracking:** Monitor progress in real-time
- **Error Handling:** Graceful fallbacks and retries
- **Logging:** Structured logs with rotation
- **VRAM Management:** Efficient memory usage
- **Progress Callbacks:** Real-time status updates

### Flexible Configuration
- **Model Selection:** 14B (quality) or 1.3B (speed)
- **Performance Tuning:** Steps, guidance scale, TeaCache
- **Multiple TTS Backends:** Dia (free) or OpenAI
- **Content Filters:** Choose your sources and topics

---

## 📊 Performance

### VRAM Requirements

| Model | Settings | VRAM | Speed | Quality |
|-------|----------|------|-------|---------|
| 1.3B | Default | ~12GB | Fast | Good |
| 14B | No optimization | 36GB | 16s/it | Excellent |
| 14B | VRAM managed | 21GB | 19s/it | Excellent |
| 14B | Max optimization | 8GB | 22s/it | Excellent |

### Speed Optimization

**Fast (testing):**
```bash
NUM_STEPS=20
TEA_CACHE_THRESH=0.15
USE_14B_MODEL=false
```

**Balanced (recommended):**
```bash
NUM_STEPS=25
TEA_CACHE_THRESH=0.14
USE_14B_MODEL=false
```

**Quality (best results):**
```bash
NUM_STEPS=50
TEA_CACHE_THRESH=0
USE_14B_MODEL=true
```

---

## 🛠️ Advanced Usage

### Multi-GPU Inference

```bash
# With sequence parallelism
torchrun --standalone --nproc_per_node=4 scripts/inference.py \
    --config configs/inference.yaml \
    --input_file examples/infer_samples.txt \
    --hp=sp_size=4,use_fsdp=True,tea_cache_l1_thresh=0.14
```

### Custom Content Sources

Edit `services/content_scraper.py`:
```python
self.rss_feeds = [
    "https://your-custom-feed.com/rss",
    "https://another-feed.com/rss",
]
```

### Voice Cloning (Dia TTS)

Install Dia TTS locally:
```bash
# See: https://github.com/nari-labs/dia/
git clone https://github.com/nari-labs/dia.git
cd dia && pip install -e .
```

Configure in `.env`:
```bash
DIA_MODEL_PATH=/path/to/dia/model
```

### Scheduled Automation

Use APScheduler for automated content generation:
```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.add_job(
    scrape_and_generate,
    'interval',
    hours=6  # Every 6 hours
)
scheduler.start()
```

---

## 🔧 Troubleshooting

### CUDA Out of Memory
```bash
# Use 1.3B model
USE_14B_MODEL=false

# Enable VRAM management
ENABLE_VRAM_MANAGEMENT=true

# Reduce steps
NUM_STEPS=20
```

### Slow Generation
```bash
# Enable TeaCache
TEA_CACHE_THRESH=0.14

# Install Flash Attention
pip install flash_attn

# Use fewer steps
NUM_STEPS=20
```

### API Key Errors
- Check `.env` file exists
- No spaces around `=` in `.env`
- API keys are valid and not expired
- Restart after changing `.env`

### Model Not Found
```bash
# Re-download
huggingface-cli download Wan-AI/Wan2.1-T2V-1.3B \
    --local-dir ./pretrained_models/Wan2.1-T2V-1.3B

# Check path
ls pretrained_models/
```

---

## 📚 Documentation

- **[SETUP.md](SETUP.md)** - Complete setup guide
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture
- **[API Docs](http://localhost:8000/docs)** - Interactive API documentation (when running)
- **[Original OmniAvatar](https://github.com/Omni-Avatar/OmniAvatar)** - Base model docs

---

## 🌟 Use Cases

### Content Creators
- Auto-generate news summary videos
- Convert blog posts to avatar presentations
- Create social media content at scale

### Businesses
- Product announcements with spokesperson
- Training videos with consistent presenter
- Customer updates and notifications

### Developers
- Integrate via REST API
- Build custom workflows
- Add to existing CMS/platforms

---

## 🤝 Contributing

Built by **BusinessBuilders** on top of [OmniAvatar](https://github.com/Omni-Avatar/OmniAvatar).

**NovaAvatar Additions:**
- Automated content pipeline
- Gradio web interface
- FastAPI REST API
- Production features

**Original OmniAvatar by:**
- [Qijun Gan](https://agnjason.github.io/)
- [Ruizi Yang](https://github.com/ZiziAmy/)
- [Jianke Zhu](https://person.zju.edu.cn/en/jkzhu)
- Zhejiang University, Alibaba Group

---

## 📄 License

Same as original OmniAvatar. See LICENSE.txt.

## 🔗 Citation

If you use NovaAvatar, please cite the original OmniAvatar:
```bibtex
@misc{gan2025omniavatar,
  title={OmniAvatar: Efficient Audio-Driven Avatar Video Generation with Adaptive Body Animation},
  author={Qijun Gan and Ruizi Yang and Jianke Zhu and Shaofei Xue and Steven Hoi},
  year={2025},
  eprint={2506.18866},
  archivePrefix={arXiv},
  primaryClass={cs.CV},
  url={https://arxiv.org/abs/2506.18866},
}
```

---

## 🙏 Acknowledgments

Thanks to:
- [OmniAvatar](https://github.com/Omni-Avatar/OmniAvatar) - Base model
- [Wan2.1](https://github.com/Wan-Video/Wan2.1) - Text-to-video foundation
- [Dia TTS](https://github.com/nari-labs/dia/) - Open-source TTS
- [Flux](https://replicate.com/black-forest-labs/flux-schnell) - Image generation
- OpenAI - GPT-4 and TTS

---

## 📞 Support

- **NovaAvatar Issues:** [GitHub Issues](https://github.com/BusinessBuilders/NovaAvatar/issues)
- **Original OmniAvatar:** [ganqijun@zju.edu.cn](mailto:ganqijun@zju.edu.cn)
- **Project Homepage:** https://omni-avatar.github.io/

---

**Ready to create automated avatar videos? Run `python run.py` and visit http://localhost:7860 to get started!** 🚀

"""
NovaAvatar Gradio Web Interface
Production-ready web UI for automated avatar video generation.
"""

import os
import sys
from pathlib import Path
import asyncio
from typing import List, Tuple, Optional

import gradio as gr
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.orchestrator import PipelineOrchestrator, JobStatus
from services.content_scraper import ContentItem
from services.script_generator import ScriptStyle


class NovaAvatarApp:
    """Gradio application for NovaAvatar."""

    def __init__(self):
        """Initialize the application."""

        self.orchestrator = PipelineOrchestrator()
        self.scraped_items = []
        self.selected_items = []

        logger.info("NovaAvatar app initialized")

    def build_interface(self) -> gr.Blocks:
        """Build the Gradio interface."""

        with gr.Blocks(
            title="NovaAvatar - Automated Avatar Video Generator",
            theme=gr.themes.Soft()
        ) as app:

            gr.Markdown("""
            # 🎬 NovaAvatar - Automated Avatar Video Generator

            Create professional avatar videos automatically from trending content.

            **Pipeline:** Content Scraping → Script Generation → Background Creation → TTS → Avatar Video
            """)

            with gr.Tabs() as tabs:

                # Dashboard Tab
                with gr.Tab("📊 Dashboard"):
                    self._build_dashboard_tab()

                # Content Scraper Tab
                with gr.Tab("🔍 Content Scraper"):
                    self._build_scraper_tab()

                # Manual Create Tab
                with gr.Tab("✏️ Manual Create"):
                    self._build_manual_tab()

                # Review Queue Tab
                with gr.Tab("📋 Review Queue"):
                    self._build_queue_tab()

                # Settings Tab
                with gr.Tab("⚙️ Settings"):
                    self._build_settings_tab()

        return app

    def _build_dashboard_tab(self):
        """Build the dashboard tab."""

        gr.Markdown("## Dashboard")

        with gr.Row():
            with gr.Column():
                total_jobs = gr.Number(label="Total Jobs", value=0, interactive=False)
                completed = gr.Number(label="Completed", value=0, interactive=False)

            with gr.Column():
                in_progress = gr.Number(label="In Progress", value=0, interactive=False)
                in_queue = gr.Number(label="In Review Queue", value=0, interactive=False)

        refresh_btn = gr.Button("🔄 Refresh Stats")

        recent_videos = gr.Gallery(
            label="Recent Videos",
            columns=3,
            height="auto"
        )

        def refresh_stats():
            jobs = self.orchestrator.jobs
            queue = self.orchestrator.get_review_queue()

            completed_count = sum(1 for j in jobs.values() if j.status == JobStatus.COMPLETED)
            in_progress_count = sum(1 for j in jobs.values() if j.status not in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.QUEUED_FOR_REVIEW])

            # Get recent video thumbnails
            recent = []
            for job in sorted(jobs.values(), key=lambda x: x.created_at, reverse=True)[:6]:
                if job.video_file and Path(job.video_file).exists():
                    recent.append(job.video_file)

            return len(jobs), completed_count, in_progress_count, len(queue), recent

        refresh_btn.click(
            fn=refresh_stats,
            outputs=[total_jobs, completed, in_progress, in_queue, recent_videos]
        )

    def _build_scraper_tab(self):
        """Build the content scraper tab."""

        gr.Markdown("## Scrape Content from News & Social Media")

        with gr.Row():
            search_term = gr.Textbox(
                label="Search Term (optional)",
                placeholder="e.g., AI, technology, climate change...",
                value=""
            )

        with gr.Row():
            max_items = gr.Slider(
                label="Max Items per Source",
                minimum=1,
                maximum=20,
                value=5,
                step=1
            )

        scrape_btn = gr.Button("🔍 Scrape Content", variant="primary")

        scrape_status = gr.Textbox(label="Status", lines=2)

        scraped_content = gr.Dataframe(
            headers=["Select", "Title", "Source", "Content", "Description"],
            datatype=["bool", "str", "str", "str", "str"],
            label="Scraped Content",
            interactive=True,
            wrap=True
        )

        # Preview section
        preview_btn = gr.Button("📄 Preview Article, Script & Background", variant="secondary")

        with gr.Row():
            with gr.Column():
                article_preview = gr.Textbox(
                    label="Article Preview",
                    lines=10,
                    placeholder="Article text will appear here..."
                )
            with gr.Column():
                script_preview = gr.Textbox(
                    label="Generated Script Preview",
                    lines=10,
                    placeholder="GPT-4 script will appear here..."
                )
            with gr.Column():
                background_preview = gr.Image(
                    label="Generated Background Preview",
                    type="filepath"
                )

        with gr.Row():
            avatar_image = gr.Image(
                label="Avatar/Composite Image",
                type="filepath",
                value="examples/images/bill.png"
            )
            use_flux = gr.Checkbox(
                label="Generate Background with Flux Dev (CPU offload enabled for 24GB GPUs)",
                value=True,
                info="If enabled: auto-generates background (slower due to CPU offload). If disabled: upload your own image"
            )

        background_prompt = gr.Textbox(
            label="Background Prompt (for Flux generation - auto-generated from article if empty)",
            placeholder="e.g., modern office with large windows, city skyline, sunset lighting...",
            lines=2
        )

        avatar_prompt = gr.Textbox(
            label="Avatar Animation Prompt (for OmniAvatar - auto-generated from article if empty)",
            placeholder="e.g., A professional presenter speaking confidently with subtle hand gestures, medium shot...",
            lines=2
        )

        with gr.Row():
            style_choice = gr.Dropdown(
                label="Script Style",
                choices=[s.value for s in ScriptStyle],
                value=ScriptStyle.PROFESSIONAL.value
            )

            duration = gr.Slider(
                label="Target Duration (seconds)",
                minimum=15,
                maximum=90,
                value=45,
                step=5
            )

        generate_btn = gr.Button("🎬 Generate Videos from Selected", variant="primary")

        generation_progress = gr.Textbox(label="Generation Progress", lines=3)

        async def scrape_content(search_term_val, max_items_val):
            try:
                # Pass search_term if provided
                search = search_term_val.strip() if search_term_val else None

                self.scraped_items = await self.orchestrator.scrape_content(
                    max_items=int(max_items_val),
                    search_term=search
                )

                # Format for dataframe
                data = []
                full_text_count = 0
                for item in self.scraped_items:
                    # Add indicator for full text availability
                    has_full_text = item.full_text and len(item.full_text) > 100
                    if has_full_text:
                        full_text_count += 1
                        status = "✓ Full"
                    else:
                        status = "⚠️ Desc"

                    data.append([
                        False,  # checkbox
                        item.title,
                        item.source_name,
                        status,
                        item.description[:100] + "..."
                    ])

                search_msg = f" for '{search}'" if search else ""
                return f"✅ Scraped {len(self.scraped_items)} items{search_msg} ({full_text_count} full articles)", data

            except Exception as e:
                logger.error(f"Scraping failed: {e}")
                return f"❌ Error: {str(e)}", []

        async def preview_article(dataframe_data, style, dur, bg_prompt, use_flux_val):
            try:
                # Validate scraped items exist
                if not self.scraped_items:
                    return "⚠️ Please scrape content first", "", None

                # Get selected items
                selected = []
                for i, row in enumerate(dataframe_data):
                    if i >= len(self.scraped_items):
                        logger.warning(f"Row index {i} exceeds scraped_items length {len(self.scraped_items)}")
                        continue
                    if row[0]:  # checkbox is True
                        selected.append(self.scraped_items[i])

                if not selected:
                    return "⚠️ No items selected", "", None

                # Preview first selected item only
                item = selected[0]
                logger.info(f"Previewing: {item.title}")

                # Fetch full article
                article_text = "Fetching article...\n\n"
                if item.url:
                    full_text = await self.orchestrator.content_scraper.fetch_full_article(item.url)
                    if full_text:
                        # Show first 1500 characters
                        article_text = f"📰 {item.title}\n\n"
                        article_text += f"Source: {item.source_name}\n"
                        article_text += f"URL: {item.url}\n\n"
                        article_text += "--- Article Text ---\n\n"
                        article_text += full_text[:1500]
                        if len(full_text) > 1500:
                            article_text += f"\n\n... ({len(full_text) - 1500} more characters)"
                    else:
                        article_text = f"❌ Could not fetch article from {item.url}\n\n"
                        article_text += f"Using description instead:\n\n{item.description}"
                        full_text = item.description
                else:
                    article_text = f"ℹ️ No URL available\n\n{item.description}"
                    full_text = item.description

                # Generate script preview
                script_text = "Generating script preview with GPT-4...\n"
                script = await self.orchestrator.script_generator.generate_script(
                    content_title=item.title,
                    content_description=full_text if full_text else item.description,
                    style=ScriptStyle(style),
                    duration=int(dur)
                )

                # Calculate word count
                word_count = len(script.script.split())

                script_text = f"🎬 Generated Script ({word_count} words, ~{script.duration_estimate}s)\n\n"
                script_text += f"Style: {style}\n"
                script_text += f"Target Duration: {dur}s\n\n"
                script_text += "--- Script ---\n\n"
                script_text += script.script
                script_text += f"\n\n--- Scene Description (for Flux) ---\n\n"
                script_text += script.scene_description
                script_text += f"\n\n--- Avatar Prompt (for OmniAvatar) ---\n\n"
                script_text += script.avatar_prompt

                # Generate background preview (only if Flux enabled)
                background_path = None
                if use_flux_val:
                    bg_description = bg_prompt if bg_prompt else script.scene_description
                    logger.info(f"Generating background preview: {bg_description[:100]}...")

                    background = await self.orchestrator.image_generator.generate_background(
                        scene_description=bg_description,
                        style="photorealistic"
                    )

                    # Cleanup Flux immediately after generation
                    self.orchestrator.image_generator.cleanup()

                    background_path = background.image_path
                    logger.info(f"Background preview generated: {background_path}")
                else:
                    logger.info("Flux disabled, skip background generation in preview")

                # Return avatar_prompt as 4th value so it can populate the textbox
                return article_text, script_text, background_path, script.avatar_prompt

            except Exception as e:
                logger.error(f"Preview failed: {e}")
                return f"❌ Error: {str(e)}", "", None, ""

        async def generate_selected(dataframe_data, style, dur, avatar_img, bg_prompt, av_prompt, use_flux_val):
            try:
                # Validate scraped items exist
                if not self.scraped_items:
                    return "⚠️ Please scrape content first"

                # Get selected items
                selected = []
                for i, row in enumerate(dataframe_data):
                    if i >= len(self.scraped_items):
                        logger.warning(f"Row index {i} exceeds scraped_items length {len(self.scraped_items)}")
                        continue
                    if row[0]:  # checkbox is True
                        selected.append(self.scraped_items[i])

                if not selected:
                    return "⚠️ No items selected"

                # Generate videos
                progress_text = f"Generating {len(selected)} videos...\n"
                progress_text += f"Image: {avatar_img}\n"

                if use_flux_val:
                    if bg_prompt:
                        progress_text += f"Mode: Flux with custom prompt + compositing\n\n"
                    else:
                        progress_text += "Mode: Flux auto-generated + compositing\n\n"
                else:
                    progress_text += "Mode: Using image as-is (no Flux/compositing)\n\n"

                for i, item in enumerate(selected):
                    progress_text += f"\n[{i+1}/{len(selected)}] Processing: {item.title}\n"

                    def progress_callback(percent, status):
                        nonlocal progress_text
                        progress_text += f"  {status} ({percent}%)\n"

                    job = await self.orchestrator.create_video_from_content(
                        item,
                        style=ScriptStyle(style),
                        duration=int(dur),
                        avatar_image=avatar_img,
                        background_prompt=bg_prompt if bg_prompt else None,
                        avatar_prompt=av_prompt if av_prompt else None,
                        use_flux=use_flux_val,
                        progress_callback=progress_callback
                    )

                    progress_text += f"  ✅ Complete! Job ID: {job.job_id}\n"

                progress_text += f"\n🎉 All videos generated!"

                return progress_text

            except Exception as e:
                logger.error(f"Generation failed: {e}")
                return f"❌ Error: {str(e)}"

        scrape_btn.click(
            fn=lambda s, m: asyncio.run(scrape_content(s, m)),
            inputs=[search_term, max_items],
            outputs=[scrape_status, scraped_content]
        )

        preview_btn.click(
            fn=lambda d, s, dur, bg, uf: asyncio.run(preview_article(d, s, dur, bg, uf)),
            inputs=[scraped_content, style_choice, duration, background_prompt, use_flux],
            outputs=[article_preview, script_preview, background_preview, avatar_prompt]
        )

        generate_btn.click(
            fn=lambda d, s, dur, av, bg, ap, uf: asyncio.run(generate_selected(d, s, dur, av, bg, ap, uf)),
            inputs=[scraped_content, style_choice, duration, avatar_image, background_prompt, avatar_prompt, use_flux],
            outputs=[generation_progress]
        )

    def _build_manual_tab(self):
        """Build the manual creation tab."""

        gr.Markdown("## Manually Create Avatar Video")

        with gr.Row():
            with gr.Column():
                prompt_input = gr.Textbox(
                    label="Video Prompt",
                    placeholder="A professional woman speaking about technology in a modern office...",
                    lines=3
                )

                image_input = gr.Image(
                    label="Reference Image (or use generated background)",
                    type="filepath"
                )

                audio_input = gr.Audio(
                    label="Audio File (or use TTS)",
                    type="filepath"
                )

            with gr.Column():
                # Script generation
                gr.Markdown("### Or Generate Script & Audio")

                topic_input = gr.Textbox(
                    label="Topic",
                    placeholder="AI breakthrough in healthcare"
                )

                description_input = gr.Textbox(
                    label="Topic Description",
                    lines=3,
                    placeholder="New AI system detects diseases with 95% accuracy..."
                )

                script_style = gr.Dropdown(
                    label="Style",
                    choices=[s.value for s in ScriptStyle],
                    value=ScriptStyle.PROFESSIONAL.value
                )

                generate_script_btn = gr.Button("✍️ Generate Script & Audio")

                generated_script = gr.Textbox(label="Generated Script", lines=5)

        with gr.Row():
            num_steps = gr.Slider(label="Inference Steps", minimum=10, maximum=50, value=25, step=5)
            guidance_scale = gr.Slider(label="Guidance Scale", minimum=1.0, maximum=10.0, value=4.5, step=0.5)

        create_btn = gr.Button("🎬 Create Video", variant="primary", size="lg")

        output_video = gr.Video(label="Generated Video")
        output_status = gr.Textbox(label="Status", lines=2)

        async def generate_script_audio(topic, description, style):
            try:
                # Generate script
                script = await self.orchestrator.script_generator.generate_script(
                    content_title=topic,
                    content_description=description,
                    style=ScriptStyle(style),
                    duration=45
                )

                # Generate audio
                audio = await self.orchestrator.tts_service.generate_speech(
                    text=script.script
                )

                # Generate background
                background = await self.orchestrator.image_generator.generate_background(
                    scene_description=script.scene_description
                )

                return script.script, audio.audio_path, background.image_path

            except Exception as e:
                logger.error(f"Script generation failed: {e}")
                return f"Error: {str(e)}", None, None

        generate_script_btn.click(
            fn=lambda t, d, s: asyncio.run(generate_script_audio(t, d, s)),
            inputs=[topic_input, description_input, script_style],
            outputs=[generated_script, audio_input, image_input]
        )

        async def create_video_manual(prompt, image, audio, steps, guidance):
            try:
                if not image or not audio:
                    return None, "⚠️ Please provide both image and audio"

                def progress_callback(percent, status):
                    print(f"[{percent}%] {status}")

                video = await self.orchestrator.avatar_service.generate_video(
                    prompt=prompt,
                    image_path=image,
                    audio_path=audio,
                    progress_callback=progress_callback
                )

                return video.video_path, f"✅ Video created successfully!"

            except Exception as e:
                logger.error(f"Manual creation failed: {e}")
                return None, f"❌ Error: {str(e)}"

        create_btn.click(
            fn=lambda p, i, a, s, g: asyncio.run(create_video_manual(p, i, a, s, g)),
            inputs=[prompt_input, image_input, audio_input, num_steps, guidance_scale],
            outputs=[output_video, output_status]
        )

    def _build_queue_tab(self):
        """Build the review queue tab."""

        gr.Markdown("## Review Queue - Approve Videos Before Publishing")

        refresh_btn = gr.Button("🔄 Refresh Queue")

        queue_list = gr.Dataframe(
            headers=["Job ID", "Title", "Status", "Created"],
            datatype=["str", "str", "str", "str"],
            label="Videos in Queue"
        )

        with gr.Row():
            selected_job = gr.Textbox(label="Selected Job ID", interactive=True)

        with gr.Row():
            preview_video = gr.Video(label="Video Preview")

        with gr.Row():
            approve_btn = gr.Button("✅ Approve", variant="primary")
            delete_btn = gr.Button("🗑️ Delete", variant="stop")

        action_status = gr.Textbox(label="Action Status")

        def refresh_queue():
            queue = self.orchestrator.get_review_queue()

            data = []
            for job in queue:
                title = job.script.get('title', 'Untitled') if job.script else 'Untitled'
                data.append([
                    job.job_id,
                    title,
                    job.status.value,
                    job.created_at.strftime("%Y-%m-%d %H:%M")
                ])

            return data

        def preview_job(job_id):
            job = self.orchestrator.get_job_status(job_id)
            if job and job.video_file:
                return job.video_file
            return None

        def approve_job(job_id):
            try:
                self.orchestrator.approve_video(job_id)
                return "✅ Video approved!"
            except Exception as e:
                return f"❌ Error: {str(e)}"

        def delete_job(job_id):
            try:
                self.orchestrator.delete_video(job_id)
                return "🗑️ Video deleted"
            except Exception as e:
                return f"❌ Error: {str(e)}"

        refresh_btn.click(fn=refresh_queue, outputs=[queue_list])
        selected_job.change(fn=preview_job, inputs=[selected_job], outputs=[preview_video])
        approve_btn.click(fn=approve_job, inputs=[selected_job], outputs=[action_status])
        delete_btn.click(fn=delete_job, inputs=[selected_job], outputs=[action_status])

    def _build_settings_tab(self):
        """Build the settings tab."""

        gr.Markdown("## Settings & Configuration")

        gr.Markdown("""
        ### API Keys
        Set these in your `.env` file:
        - `OPENAI_API_KEY` - For script generation
        - `REPLICATE_API_TOKEN` - For Flux image generation
        - `REDDIT_CLIENT_ID` & `REDDIT_CLIENT_SECRET` - For Reddit scraping
        - `NEWSAPI_KEY` - For news scraping
        """)

        gr.Markdown("""
        ### Model Configuration
        - **14B Model:** Higher quality, requires 21-36GB VRAM
        - **1.3B Model:** Faster, requires ~12GB VRAM
        - Edit `configs/inference.yaml` or `configs/inference_1.3B.yaml`
        """)

        gr.Markdown("""
        ### Production Tips
        1. Use Redis for job queuing in production
        2. Run Dia TTS locally for cost savings
        3. Set up automated scraping with APScheduler
        4. Monitor VRAM usage during generation
        5. Enable TeaCache for 2-3x speedup
        """)

    def launch(self, **kwargs):
        """Launch the Gradio app."""

        app = self.build_interface()

        # Default launch settings
        launch_settings = {
            "server_name": "0.0.0.0",
            "server_port": 7860,
            "share": False,
            "show_error": True,
        }

        launch_settings.update(kwargs)

        logger.info(f"Launching NovaAvatar on port {launch_settings['server_port']}...")

        app.launch(**launch_settings)


def main():
    """Main entry point."""

    # Setup logging
    logger.add(
        "logs/novaavatar_{time}.log",
        rotation="1 day",
        retention="7 days",
        level="INFO"
    )

    # Create app
    app = NovaAvatarApp()

    # Launch
    app.launch()


if __name__ == "__main__":
    main()

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
            headers=["Select", "Title", "Source", "Description"],
            datatype=["bool", "str", "str", "str"],
            label="Scraped Content",
            interactive=True,
            wrap=True
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

        async def scrape_content(max_items_val):
            try:
                self.scraped_items = await self.orchestrator.scrape_content(
                    max_items=int(max_items_val)
                )

                # Format for dataframe
                data = []
                for item in self.scraped_items:
                    data.append([
                        False,  # checkbox
                        item.title,
                        item.source_name,
                        item.description[:100] + "..."
                    ])

                return f"✅ Scraped {len(self.scraped_items)} items", data

            except Exception as e:
                logger.error(f"Scraping failed: {e}")
                return f"❌ Error: {str(e)}", []

        async def generate_selected(dataframe_data, style, dur):
            try:
                # Get selected items
                selected = []
                for i, row in enumerate(dataframe_data):
                    if row[0]:  # checkbox is True
                        selected.append(self.scraped_items[i])

                if not selected:
                    return "⚠️ No items selected"

                # Generate videos
                progress_text = f"Generating {len(selected)} videos...\n"

                for i, item in enumerate(selected):
                    progress_text += f"\n[{i+1}/{len(selected)}] Processing: {item.title}\n"

                    def progress_callback(percent, status):
                        nonlocal progress_text
                        progress_text += f"  {status} ({percent}%)\n"

                    job = await self.orchestrator.create_video_from_content(
                        item,
                        style=ScriptStyle(style),
                        duration=int(dur),
                        progress_callback=progress_callback
                    )

                    progress_text += f"  ✅ Complete! Job ID: {job.job_id}\n"

                progress_text += f"\n🎉 All videos generated!"

                return progress_text

            except Exception as e:
                logger.error(f"Generation failed: {e}")
                return f"❌ Error: {str(e)}"

        scrape_btn.click(
            fn=lambda x: asyncio.run(scrape_content(x)),
            inputs=[max_items],
            outputs=[scrape_status, scraped_content]
        )

        generate_btn.click(
            fn=lambda d, s, dur: asyncio.run(generate_selected(d, s, dur)),
            inputs=[scraped_content, style_choice, duration],
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

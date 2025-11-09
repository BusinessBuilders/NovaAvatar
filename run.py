#!/usr/bin/env python3
"""
NovaAvatar Launcher
Convenient script to run different components of the system.
"""

import sys
import argparse
import subprocess
from pathlib import Path


def run_gradio():
    """Run the Gradio web interface."""
    print("🚀 Starting Gradio Web UI...")
    print("Access at: http://localhost:7860")
    print("")

    subprocess.run([sys.executable, "frontend/app.py"])


def run_api():
    """Run the FastAPI server."""
    print("🚀 Starting FastAPI Server...")
    print("Access at: http://localhost:8000")
    print("API Docs: http://localhost:8000/docs")
    print("")

    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "api.server:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ])


def run_both():
    """Run both Gradio and FastAPI (requires tmux or screen)."""
    print("🚀 Starting both Gradio and FastAPI...")
    print("Note: This requires running in separate terminals")
    print("")
    print("Terminal 1: python run.py gradio")
    print("Terminal 2: python run.py api")
    print("")
    print("Or use tmux/screen for background processes")


def setup_env():
    """Help with environment setup."""
    print("🔧 NovaAvatar Environment Setup")
    print("=" * 50)
    print("")

    # Check if .env exists
    env_file = Path(".env")
    env_example = Path(".env.example")

    if not env_file.exists():
        if env_example.exists():
            print("❌ .env file not found")
            print("✅ .env.example exists")
            print("")
            print("Next steps:")
            print("1. Copy .env.example to .env:")
            print("   cp .env.example .env")
            print("")
            print("2. Edit .env and add your API keys:")
            print("   - OPENAI_API_KEY")
            print("   - REPLICATE_API_TOKEN")
            print("")
        else:
            print("❌ .env.example not found!")
    else:
        print("✅ .env file exists")
        print("")

    # Check model directories
    print("Checking model directories...")
    model_base = Path("pretrained_models")

    models_to_check = [
        ("Wan2.1-T2V-1.3B", "1.3B Model (faster)"),
        ("Wan2.1-T2V-14B", "14B Model (better quality)"),
        ("wav2vec2-base-960h", "Audio Encoder (required)"),
        ("OmniAvatar-1.3B", "OmniAvatar LoRA 1.3B"),
        ("OmniAvatar-14B", "OmniAvatar LoRA 14B"),
    ]

    for model_dir, description in models_to_check:
        path = model_base / model_dir
        if path.exists():
            print(f"✅ {description}")
        else:
            print(f"❌ {description} - Not found at {path}")

    print("")
    print("If models are missing, download them:")
    print("See SETUP.md for download commands")
    print("")

    # Check Python packages
    print("Checking Python environment...")

    required_packages = [
        "torch",
        "gradio",
        "fastapi",
        "openai",
        "replicate"
    ]

    missing = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing.append(package)

    if missing:
        print("")
        print("Install missing packages:")
        print("pip install -r requirements.txt")

    print("")
    print("=" * 50)
    print("Setup check complete!")


def validate_config():
    """Validate configuration."""
    print("🔍 Validating configuration...")
    print("")

    try:
        from config.settings import setup_logging, validate_settings

        setup_logging()
        valid = validate_settings()

        if valid:
            print("")
            print("✅ Configuration is valid!")
            print("You can now run the application:")
            print("  python run.py gradio")
            print("  python run.py api")
        else:
            print("")
            print("❌ Configuration has errors")
            print("Please fix the issues above")

    except Exception as e:
        print(f"❌ Error validating config: {e}")
        print("")
        print("Make sure you have:")
        print("1. Created .env file from .env.example")
        print("2. Added your API keys")
        print("3. Downloaded the required models")


def show_help():
    """Show help information."""
    print("""
NovaAvatar - Automated Avatar Video Generator
============================================

Usage: python run.py [command]

Commands:
  gradio      Start the Gradio web interface (default)
  api         Start the FastAPI server
  both        Instructions for running both
  setup       Check environment setup
  validate    Validate configuration
  help        Show this help message

Examples:
  python run.py              # Start Gradio UI
  python run.py gradio       # Start Gradio UI
  python run.py api          # Start API server
  python run.py setup        # Check setup
  python run.py validate     # Validate config

For detailed setup instructions, see SETUP.md
    """)


def main():
    parser = argparse.ArgumentParser(
        description="NovaAvatar Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "command",
        nargs="?",
        default="gradio",
        choices=["gradio", "api", "both", "setup", "validate", "help"],
        help="Command to run (default: gradio)"
    )

    args = parser.parse_args()

    commands = {
        "gradio": run_gradio,
        "api": run_api,
        "both": run_both,
        "setup": setup_env,
        "validate": validate_config,
        "help": show_help,
    }

    command = commands.get(args.command, show_help)
    command()


if __name__ == "__main__":
    main()

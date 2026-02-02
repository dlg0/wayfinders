# Installation Guide

## Prerequisites

- **Python 3.11+** (3.10 minimum, 3.11+ recommended)
- **uv** - Fast Python package installer ([install guide](https://docs.astral.sh/uv/getting-started/installation/))
- **ffmpeg** (optional but recommended) - Required for video assembly

### Installing Prerequisites

**macOS:**
```bash
brew install python@3.11 ffmpeg
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv ffmpeg
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```powershell
winget install Python.Python.3.11
winget install Gyan.FFmpeg
irm https://astral.sh/uv/install.ps1 | iex
```

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/dlg0/wayfinders.git
   cd wayfinders
   ```

2. **Create virtual environment and install dependencies:**
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -e ".[dev,placeholders]"
   ```

3. **Verify installation:**
   ```bash
   wf --help
   ```

## Configuration (wf.toml)

Copy the example configuration:
```bash
cp wf.toml.example wf.toml
```

### Provider Setup

The `wf.toml` file configures asset generation providers:

```toml
# Default provider for image generation
default_provider = "placeholder"

[providers.placeholder]
# No configuration needed - generates colored rectangles with labels
# Perfect for development and testing

[providers.openai]
# OpenAI image generation (requires API key)
api_key_env = "OPENAI_API_KEY"  # Environment variable containing API key
model = "gpt-image-1"           # Model to use for generation
```

**Available Providers:**
- `placeholder` - Generates simple colored rectangles (no API key needed)
- `openai` - Uses OpenAI's image generation API (requires `OPENAI_API_KEY`)

To use OpenAI:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

## Quick Start

Build the sample episode:

```bash
# Validate the episode YAML
uv run wf validate episodes/s01e01_map_forgot_roads/episode.yaml --allow-missing-assets

# Generate placeholder assets
uv run wf placeholders episodes/s01e01_map_forgot_roads/episode.yaml

# Create a build plan
uv run wf plan episodes/s01e01_map_forgot_roads/episode.yaml

# Build timeline and animatic
uv run wf build-timeline episodes/s01e01_map_forgot_roads/episode.yaml
uv run wf build-animatic episodes/s01e01_map_forgot_roads/episode.yaml
```

Outputs are written to `episodes/s01e01_map_forgot_roads/logs/`.

## Troubleshooting

### "command not found: wf"

Ensure your virtual environment is activated:
```bash
source .venv/bin/activate
```

Or run via uv:
```bash
uv run wf --help
```

### "ffmpeg not found" warning

The video assembly step requires ffmpeg. Install it:
- macOS: `brew install ffmpeg`
- Ubuntu: `sudo apt install ffmpeg`
- Windows: `winget install Gyan.FFmpeg`

Without ffmpeg, the pipeline will skip video assembly but still produce the timeline and frame assets.

### Validation errors with missing assets

Use `--allow-missing-assets` during development:
```bash
uv run wf validate episode.yaml --allow-missing-assets
```

Then generate placeholders:
```bash
uv run wf placeholders episode.yaml
```

### Python version errors

Ensure Python 3.11+ is installed and active:
```bash
python --version  # Should show 3.11+
```

With uv, you can install a specific version:
```bash
uv python install 3.11
uv python pin 3.11
```

### Import errors after installation

Reinstall in editable mode:
```bash
uv pip install -e ".[dev,placeholders]"
```

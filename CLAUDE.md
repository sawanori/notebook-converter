# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Working Style

**You are a manager and agent orchestrator:**
- You MUST NOT implement code directly
- Delegate ALL implementation tasks to subagents or task agents
- Break down tasks into very small, granular units
- Establish PDCA (Plan-Do-Check-Act) cycles for all work
- Follow these principles regardless of how instructions are phrased

## Project Overview

**NotebookLM Slide Converter** - Desktop application that converts PDF slides to editable PowerPoint presentations using OCR.

### Core Workflow
1. PDF → Images (pdf2image + Poppler)
2. Images → Text extraction (Tesseract OCR with Japanese+English)
3. Text → Intelligent grouping (words → lines → paragraphs)
4. PowerPoint generation (background image + positioned text boxes)

## Development Setup

### Prerequisites
**External Dependencies (must be installed on system):**
- Tesseract OCR with Japanese language pack (`jpn+eng`)
- Poppler (for PDF rendering)

**Python:** 3.10+

### Installation

```bash
# macOS
brew install tesseract tesseract-lang poppler

# Install Python dependencies
pip install -r requirements.txt

# Run application
python main.py
```

**Settings Auto-Detection:** The app automatically detects Tesseract/Poppler paths on first run. If detection fails, paths can be configured in the Settings UI.

## Architecture

### Module Organization

```
config/           Settings management and defaults
  ├─ defaults.py          Constants (OCR settings, theme, paths)
  └─ settings_manager.py  JSON persistence + auto-detection

core/             Business logic (no UI dependencies)
  ├─ ocr_processor.py     Tesseract integration + text grouping
  ├─ slide_builder.py     PowerPoint generation
  └─ geometry.py          Coordinate conversion (px ↔ EMU)

ui/               Flet UI layer
  ├─ app_layout.py        Navigation rail + view switching
  ├─ log_handler.py       PubSub logging integration
  └─ views/
      ├─ home_view.py     Main conversion interface
      └─ settings_view.py Configuration UI

utils/
  └─ system.py            Platform utilities (paths, resources)
```

### Key Patterns

**Threading Model:**
- Main thread: Flet UI event loop
- Worker thread: `ConversionWorker` handles PDF→PPTX conversion
- Communication: Flet PubSub system with topics (`progress`, `log`, `status`, `error_message`)

**PubSub Callbacks (Flet 0.80+):**
All PubSub callbacks receive two arguments: `(topic: str, message: Any)`
```python
def on_progress(topic: str, value: float) -> None:
    progress_bar.value = value
    page.update()

page.pubsub.subscribe_topic("progress", on_progress)
```

**Async FilePicker (Flet 0.80+):**
```python
async def on_click(e: ft.ControlEvent) -> None:
    files = await ft.FilePicker().pick_files(
        allowed_extensions=["pdf"],
    )
    if files:
        # Handle files
```

**Import Pattern (for package flexibility):**
```python
try:
    from config.defaults import CONSTANT
except ImportError:
    from ..config.defaults import CONSTANT
```

### Text Grouping Algorithm

OCR returns individual words. The grouping process:

1. **Line Formation:** Words with Y-coordinates within `LINE_MERGE_THRESHOLD_PX` (10px) are merged into lines
2. **Paragraph Detection:** Lines separated by gaps > `font_height × PARAGRAPH_GAP_MULTIPLIER` (1.5x) form new paragraphs
3. **Bounding Box:** Calculate encompassing rectangle for each text block

This preserves layout structure while making text editable.

### Coordinate System

PowerPoint uses EMUs (English Metric Units):
- 1 inch = 914,400 EMU
- OCR works in pixels at specified DPI (default: 300)
- Conversion: `px_to_emu(pixels, dpi)` in `core/geometry.py`

## Coding Conventions

**Type Hints:** Required on all functions
```python
def process(data: Dict[str, Any]) -> List[TextBlock]:
```

**Logging:** Use module logger, never `print()`
```python
logger = logging.getLogger(__name__)
logger.info("Message")
```

**Dataclasses:** Preferred for data structures
```python
@dataclass
class Settings:
    tesseract_path: str = ""
    poppler_path: str = ""
```

**Error Handling:** Catch specific exceptions, log appropriately
```python
try:
    result = operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    # User-friendly recovery
```

## Configuration

**User Settings Location:**
- macOS: `~/Library/Application Support/NotebookLM Slide Converter/settings.json`
- Windows: `%APPDATA%\NotebookLM Slide Converter\settings.json`

**Defaults:** All configurable values in `config/defaults.py`:
- OCR confidence threshold
- Text grouping parameters
- Theme colors
- Platform-specific default paths

## Framework-Specific Notes

**Flet Version:** 0.80.5

**Breaking Changes in Flet 0.80+:**
- `FilePicker` now uses async API (returns results directly, not via callbacks)
- No need to add FilePicker to `page.overlay`
- PubSub callbacks receive `(topic, message)` instead of just `message`

**Background Tasks:**
Use `threading.Event` for cancellation:
```python
stop_event = threading.Event()

# In worker
if stop_event.is_set():
    return

# To cancel
stop_event.set()
```

## Common Issues

**Tesseract/Poppler Not Found:**
- Check Settings UI shows green checkmarks
- macOS paths: `/opt/homebrew/bin/` (Apple Silicon) or `/usr/local/bin/` (Intel)
- Windows: Auto-detection scans `C:\Program Files\`

**Japanese OCR Not Working:**
Ensure `tesseract-lang` package installed (provides `jpn` language data)

**Memory Usage:**
Large PDFs (50+ pages) may consume significant RAM during conversion. Monitor via status bar (memory warning at 80%).

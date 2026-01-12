# UI Element Detection Setup Guide

This guide explains how to set up and use the OmniParser-based UI element detection feature for the browser automation agent.

## Overview

The element detection system automatically identifies UI elements (buttons, inputs, text, etc.) from screenshots and provides their positions to the AI agent. This eliminates the need for hardcoded coordinates in skills, making the agent work across different screen sizes.

**Key Benefits:**
- Screen-size agnostic automation
- Semantic element understanding ("Send button", "Search input")
- Automatic coordinate detection
- No manual coordinate mapping needed

## Prerequisites

- Python 3.12 or higher
- HuggingFace CLI (`pip install huggingface-hub`)
- ~1GB disk space for model weights
- ~1GB RAM when models are loaded
- GPU recommended but not required (CPU inference works)

## Installation

### 1. Install Python Dependencies

From the `servers/agents/` directory:

```bash
# Install all dependencies including OmniParser packages
uv sync
```

This installs:
- `ultralytics` - YOLOv8 for detection
- `transformers` - Florence for captioning
- `torch` / `torchvision` - PyTorch framework
- `pillow` - Image processing
- `safetensors` - Model loading
- `huggingface-hub` - Model download

### 2. Download OmniParser Weights

Run the setup script to download model weights from HuggingFace:

```bash
# From servers/agents/ directory
./scripts/setup_omniparser.sh
```

This downloads:
- **Detection model** (~100MB): YOLOv8 trained for UI element detection
- **Caption model** (~900MB): Florence model for semantic captioning

Models are saved to `./weights/` directory (gitignored).

**Manual download (if script fails):**
```bash
huggingface-cli download microsoft/OmniParser-v2.0 \
    icon_detect/model.pt icon_detect/model.yaml icon_detect/train_args.yaml \
    icon_caption/config.json icon_caption/generation_config.json icon_caption/model.safetensors \
    --local-dir ./weights

mv ./weights/icon_caption ./weights/icon_caption_florence
```

### 3. Verify Installation

Run the integration tests with your sample image:

```bash
# From servers/agents/ directory
pytest tests/test_element_detection_integration.py -v -s
```

Expected output:
```
test_detect_elements_from_whatsapp_screenshot PASSED
  Detected 15 UI elements:
    [1] Input "Ask Meta AI or Search" at grid (12, 8) [confidence: 0.92]
    [2] Text "Erwin Chandra Saputra" at grid (15, 25) [confidence: 0.88]
    [3] Button "Get from App Store" at grid (85, 90) [confidence: 0.91]
    ...
```

## Usage

### Starting the Server

```bash
cd servers/agents
langgraph dev
```

Element detection runs automatically for every screenshot received.

### Environment Variables

Control element detection behavior with environment variables:

```bash
# Enable/disable element detection (default: true)
export ELEMENT_DETECTION_ENABLED=true

# Custom weights directory (default: ./weights)
export OMNIPARSER_WEIGHTS_DIR=/path/to/weights
```

**Disable element detection** temporarily:
```bash
ELEMENT_DETECTION_ENABLED=false langgraph dev
```

### How It Works

**Execution Flow:**
```
Client sends screenshot
    ↓
Element Detection Node (NEW)
  - Runs YOLOv8 detection (~100ms)
  - Generates captions (~500ms)
  - Converts to 0-100 grid
    ↓
Model Node
  - Receives screenshot + detected elements
  - Makes informed decisions
    ↓
Tool Node executes action
    ↓
Loop back through Element Detection
```

**Agent receives context like:**
```
Detected UI Elements:
- [1] Input "Ask Meta AI or Search" at grid (12, 8)
- [2] Button "New chat" at grid (5, 5)
- [3] Text "Erwin Chandra Saputra" at grid (15, 25)
- [4] Button "Get from App Store" at grid (85, 90)
```

The model can now reference elements semantically:
- "Click the search input at (12, 8)"
- "Find element [3] containing 'Erwin' and click it"

### Writing Screen-Size Agnostic Skills

**Before (hardcoded):**
```markdown
## Common Actions
- Search bar: x=12, y=8
- Send button: x=95, y=92
```

**After (semantic):**
```markdown
## Element Identification
Use detected elements to find:
- **Search bar**: Look for Input with caption containing "Search"
- **Send button**: Look for Button near message input
```

See `prompts/skills/whatsapp-web.skill.prompt.md` for a complete example.

## Performance

### Latency

| Operation | Time | Notes |
|-----------|------|-------|
| YOLOv8 Detection | ~100ms | CPU inference |
| Florence Captioning | ~500ms | For all elements |
| **Total per screenshot** | **~600ms** | Acceptable for conversational agent |

### Optimization Tips

1. **Use GPU**: Set `CUDA_VISIBLE_DEVICES=0` for 5-10x faster inference
2. **Reduce elements**: Lower YOLO confidence threshold if too many false positives
3. **Cache aggressively**: Elements are cached per screenshot automatically
4. **Disable when not needed**: Set `ELEMENT_DETECTION_ENABLED=false` for debugging

## Testing

### Run All Tests

```bash
# Unit tests (no models required)
pytest tests/test_element_detector.py -v

# Integration tests (requires models)
pytest tests/test_element_detection_integration.py -v -s
```

### Test with Your Own Images

Add images to `tests/images/` and create a test:

```python
def test_my_screenshot():
    image_path = Path(__file__).parent / "images" / "my_screenshot.png"
    with open(image_path, "rb") as f:
        img_bytes = f.read()

    img = Image.open(image_path)
    b64 = base64.b64encode(img_bytes).decode("utf-8")

    elements = detect_elements_from_screenshot(
        f"data:image/png;base64,{b64}",
        img.width,
        img.height
    )

    print(f"Detected {len(elements)} elements:")
    for elem in elements:
        print(f"  - {elem.element_type}: {elem.caption} at {elem.grid_center}")
```

## Troubleshooting

### Models Not Loading

**Error:** `FileNotFoundError: Detection model not found at weights/icon_detect/model.pt`

**Solution:** Run `./scripts/setup_omniparser.sh` to download models.

### Low Detection Accuracy

**Issue:** Not detecting expected elements

**Solutions:**
1. Check image quality - OmniParser works best with clear UI screenshots
2. Lower YOLO confidence threshold (edit `element_detector.py:_detect_ui_elements`)
3. Ensure screenshot is RGB format (not RGBA or grayscale)

### High Memory Usage

**Issue:** Process using >2GB RAM

**Solutions:**
1. Models are loaded once and cached - this is expected
2. Run on GPU to offload memory from RAM to VRAM
3. Disable detection if not needed: `ELEMENT_DETECTION_ENABLED=false`

### Slow Inference

**Issue:** Each screenshot takes >2 seconds

**Solutions:**
1. Use GPU: `CUDA_VISIBLE_DEVICES=0 langgraph dev`
2. Reduce image resolution before detection
3. Skip captioning for speed (modify `element_detector.py`)

## Architecture Details

### Key Components

| Component | Purpose | Location |
|-----------|---------|----------|
| `element_detector.py` | OmniParser wrapper service | `src/agents/browser_agent/services/` |
| `element_detection_node.py` | LangGraph node | `src/agents/browser_agent/nodes/` |
| `state.py` | State dataclasses | `src/agents/browser_agent/` |
| `model_node.py` | Injects elements into prompt | `src/agents/browser_agent/nodes/` |
| `agent.py` | Graph with detection flow | `src/agents/browser_agent/` |

### Data Flow

1. **Screenshot arrives** → `current_screenshot` in state
2. **Element detection node** runs `detect_elements_from_screenshot()`
3. **Detected elements** → `detected_elements` in state
4. **Model node** calls `format_elements_for_prompt()` and appends to system prompt
5. **Model receives** enhanced prompt with semantic element data
6. **Tool executes** action using coordinates from detected elements
7. **New screenshot** clears `detected_elements` (re-detected in next loop)

### Coordinate System

**Pixel → Grid Conversion:**
```python
grid_x = int((pixel_x / viewport_width) * 100)
grid_y = int((pixel_y / viewport_height) * 100)
```

**Example:**
- Viewport: 1920x1080
- Element center: (960px, 540px)
- Grid coordinates: (50, 50) ← center of screen

## License Notes

- **Detection model (YOLOv8)**: AGPL-3.0 (inherited from Ultralytics)
- **Caption model (Florence)**: MIT
- **Your code**: Keep as-is

⚠️ **Commercial use**: Verify AGPL compatibility with your legal team if deploying commercially. The detection model's AGPL license may require your modifications to be open-sourced.

## Support

- **Issues**: File bugs at `anna-monorepo` GitHub issues
- **Questions**: Check existing skills in `prompts/skills/` for examples
- **Performance**: See optimization tips above

---

**Next Steps:**
1. ✅ Install dependencies and download models
2. ✅ Run tests to verify installation
3. ✅ Start server and test with WhatsApp Web
4. 📝 Migrate your custom skills to semantic descriptions
5. 🚀 Deploy and monitor performance

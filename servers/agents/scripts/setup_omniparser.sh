#!/bin/bash
# Download OmniParser model weights

set -e

WEIGHTS_DIR="${1:-./weights}"
mkdir -p "$WEIGHTS_DIR"

echo "Downloading OmniParser V2 weights to $WEIGHTS_DIR..."

# Download detection model (YOLOv8)
echo "Downloading YOLO detection model..."
uv run huggingface-cli download microsoft/OmniParser-v2.0 \
    icon_detect/train_args.yaml \
    icon_detect/model.pt \
    icon_detect/model.yaml \
    --local-dir "$WEIGHTS_DIR"

# Download caption model files from OmniParser
echo "Downloading caption model..."
uv run huggingface-cli download microsoft/OmniParser-v2.0 \
    icon_caption/config.json \
    icon_caption/generation_config.json \
    icon_caption/model.safetensors \
    icon_caption/LICENSE \
    --local-dir "$WEIGHTS_DIR"

# Download additional Florence tokenizer files
echo "Downloading Florence tokenizer files..."
uv run huggingface-cli download microsoft/Florence-2-base-ft \
    preprocessor_config.json \
    processing_florence2.py \
    vocab.json \
    tokenizer.json \
    tokenizer_config.json \
    --local-dir "$WEIGHTS_DIR/icon_caption"

# Rename caption folder as expected by code
if [ -d "$WEIGHTS_DIR/icon_caption" ]; then
    if [ -d "$WEIGHTS_DIR/icon_caption_florence" ]; then
        rm -rf "$WEIGHTS_DIR/icon_caption_florence"
    fi
    mv "$WEIGHTS_DIR/icon_caption" "$WEIGHTS_DIR/icon_caption_florence"
fi

echo ""
echo "✅ Done! Weights downloaded to $WEIGHTS_DIR"
echo ""
echo "NOTE: Florence captioning is temporarily disabled due to compatibility issues."
echo "YOLO detection works perfectly and provides accurate element coordinates."
echo ""
echo "Run tests:"
echo "  pytest tests/browser_agent/test_element_detection_integration.py -v"

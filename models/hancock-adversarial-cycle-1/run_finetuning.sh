#!/bin/bash
#
# Hancock Fine-Tuning Script - Adversarial Cycle 1
# =================================================
#

set -e

echo "🚀 Hancock Fine-Tuning - Adversarial Cycle 1"
echo "=" * 80
echo ""

# Configuration
DATASET="/home/_0ai_/Hancock-1/data/hancock_adversarial_cycle_1.jsonl"
OUTPUT_DIR="/home/_0ai_/Hancock-1/models/hancock-adversarial-cycle-1"
MODEL_BASE="mistralai/mistral-7b-instruct-v0.3"

echo "📦 Dataset: $DATASET"
echo "🎯 Output: $OUTPUT_DIR"
echo "🔧 Base Model: $MODEL_BASE"
echo ""

# Check if hancock_finetune_v3.py exists
if [ -f "/home/_0ai_/Hancock-1/hancock_finetune_v3.py" ]; then
    echo "🔥 Starting fine-tuning with hancock_finetune_v3.py..."
    echo ""
    
    cd /home/_0ai_/Hancock-1
    
    python3 hancock_finetune_v3.py \
        --dataset "$DATASET" \
        --output "$OUTPUT_DIR" \
        --epochs 3 \
        --batch-size 4 \
        --learning-rate 2e-4 \
        --max-seq-length 2048
else
    echo "⚠️  hancock_finetune_v3.py not found"
    echo ""
    echo "📝 Manual fine-tuning steps:"
    echo "   1. cd /home/_0ai_/Hancock-1"
    echo "   2. python3 hancock_finetune_v3.py --dataset $DATASET --output $OUTPUT_DIR"
    echo ""
fi

echo ""
echo "✅ Fine-tuning configuration complete!"
echo ""

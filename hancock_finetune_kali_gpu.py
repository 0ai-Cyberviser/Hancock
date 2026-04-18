#!/usr/bin/env python3
# Hancock Fine-Tune — Kali GPU Edition (CyberViser)
# Run with: source .venv_hancock_finetune/bin/activate && python hancock_finetune_kali_gpu.py

import os, json, torch
from pathlib import Path
from datasets import Dataset
from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import TrainingArguments

print("🔥 Hancock Fine-Tune — Kali GPU Edition (v0.4.1)")

# 1. Dataset (v3 preferred)
dataset_path = Path("data/hancock_v3.jsonl")
if not dataset_path.exists():
    dataset_path = Path("data/hancock_v2.jsonl")
if not dataset_path.exists():
    print("Generating v3 dataset...")
    os.system("python hancock_pipeline.py --phase 3")
    dataset_path = Path("data/hancock_v3.jsonl")

data = [json.loads(l) for l in dataset_path.read_text().strip().splitlines()]
print(f"✅ Loaded {len(data):,} samples")

# 2. Model
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="mistralai/Mistral-7B-Instruct-v0.3",
    max_seq_length=2048,
    dtype=None,
    load_in_4bit=True,
)
model = FastLanguageModel.get_peft_model(
    model,
    r=32,
    target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],
    lora_alpha=32, lora_dropout=0.05, bias="none",
    use_gradient_checkpointing="unsloth", random_state=42,
)

# 3. Format
texts = [tokenizer.apply_chat_template(s["messages"], tokenize=False, add_generation_prompt=False) for s in data]
ds = Dataset.from_dict({"text": texts}).train_test_split(test_size=0.05, seed=42)

# 4. Train
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=ds["train"],
    eval_dataset=ds["test"],
    dataset_text_field="text",
    max_seq_length=2048,
    packing=True,
    args=TrainingArguments(
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        warmup_ratio=0.05,
        num_train_epochs=3,
        learning_rate=2e-4,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=20,
        eval_strategy="steps",
        eval_steps=100,
        save_strategy="steps",
        save_steps=200,
        save_total_limit=2,
        output_dir="/content/hancock_checkpoints",
        report_to="none",
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        seed=42,
    ),
)

print(f"VRAM before training: {torch.cuda.memory_allocated(0)/1e9:.1f}/{torch.cuda.get_device_properties(0).total_memory/1e9:.1f} GB")
result = trainer.train()
print(f"✅ Training complete — final loss: {result.training_loss:.4f}")

# 5. Save
model.save_pretrained("hancock_lora")
tokenizer.save_pretrained("hancock_lora")
print("✅ LoRA adapters saved to ./hancock_lora")

# Optional GGUF (Unsloth handles it)
try:
    model.save_pretrained_gguf("hancock_gguf", tokenizer, quantization_method="q4_k_m")
    print("✅ GGUF Q4_K_M ready for Ollama")
except Exception as e:
    print(f"⚠️ GGUF export skipped: {e}")

print("🎉 Fine-tune finished! Next: `ollama create hancock -f Modelfile.hancock`")

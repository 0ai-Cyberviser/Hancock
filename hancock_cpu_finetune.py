#!/usr/bin/env python3
"""
Hancock CPU Fine-Tune
CyberViser | hancock_cpu_finetune.py

Fine-tunes TinyLlama-1.1B-Chat locally on CPU using LoRA.
Designed for machines without a CUDA GPU (AMD / CPU-only).

Model: TinyLlama/TinyLlama-1.1B-Chat-v1.0  (~2.2 GB in float32)
Data:  data/hancock_v2.jsonl  (1375 samples)

Usage:
    python hancock_cpu_finetune.py                  # full run
    python hancock_cpu_finetune.py --max-steps 20   # smoke test
    python hancock_cpu_finetune.py --debug          # verbose + 10 steps
    python hancock_cpu_finetune.py --test           # load saved adapter

Output: hancock-cpu-adapter/
"""
import argparse
import json
import os
import time
import sys
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────
DATASET_PATH = Path(__file__).parent / "data" / "hancock_v2.jsonl"
OUTPUT_DIR   = Path(__file__).parent / "hancock-cpu-adapter"
MODEL_NAME   = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
MODEL_REVISION = "fe8a4ea1ffedaf415f4da2f062534de366a451e6"
MAX_SEQ_LEN  = 1024   # keep low for CPU RAM
LORA_R       = 8
LORA_ALPHA   = 16

HANCOCK_SYSTEM = (
    "You are Hancock, an elite cybersecurity specialist built by CyberViser. "
    "You operate as both a penetration tester and SOC analyst. "
    "You operate STRICTLY within authorized scope. You always confirm authorization "
    "before suggesting active techniques and recommend responsible disclosure."
)

FINETUNE_DEPS_HINT = (
    "Missing fine-tuning dependency. Run `make finetune-install` "
    "or `pip install -r requirements-finetune.txt` first."
)


def parse_args():
    p = argparse.ArgumentParser(description="Hancock CPU LoRA fine-tune (TinyLlama 1.1B)")
    p.add_argument("--max-steps", type=int, default=200,
                   help="Training steps (default: 200, ~30-60 min on CPU)")
    p.add_argument("--batch-size", type=int, default=1,
                   help="Per-device batch size (default: 1 for CPU RAM)")
    p.add_argument("--grad-accum", type=int, default=8,
                   help="Gradient accumulation (default: 8, effective batch=8)")
    p.add_argument("--lora-r", type=int, default=LORA_R, help="LoRA rank")
    p.add_argument("--patience", type=int, default=3,
                   help="Early stopping patience (default: 3)")
    p.add_argument("--max-samples", type=int, default=None,
                   help="Limit samples for quick tests (e.g. --max-samples 200)")
    p.add_argument("--dataset", type=str, default=None,
                   help="Path to training JSONL (default: data/hancock_v2.jsonl; use data/hancock_v3.jsonl for v3)")
    p.add_argument("--max-seq-len", type=int, default=MAX_SEQ_LEN,
                   help=f"Max sequence length (default: {MAX_SEQ_LEN}; use 512 to halve training time)")
    p.add_argument("--hf-push", type=str, default=None,
                   help="HuggingFace repo to push adapter after training (e.g. cyberviser/hancock-tinyllama)")
    p.add_argument("--debug", action="store_true",
                   help="Debug mode: 10 steps, 50 samples, verbose")
    p.add_argument("--test", action="store_true",
                   help="Load the saved adapter and run sample prompts")
    return p.parse_args()


def load_dataset(path: Path, max_samples=None, debug=False):
    """Load hancock_v2.jsonl and convert to HuggingFace Dataset."""
    from datasets import Dataset

    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    if debug:
        records = records[:50]
    elif max_samples:
        records = records[:max_samples]

    print(f"[dataset] Loaded {len(records):,} samples from {path.name}")
    return Dataset.from_list(records)


def format_sample(sample, tokenizer):
    """Apply TinyLlama chat template to a sample with messages."""
    messages = sample["messages"]

    # Inject Hancock system prompt if system message exists
    if messages and messages[0]["role"] == "system":
        messages = [{"role": "system", "content": HANCOCK_SYSTEM}] + messages[1:]

    try:
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False,
        )
    except Exception:
        # Fallback: manual format
        text = f"<|system|>\n{HANCOCK_SYSTEM}</s>\n"
        for m in messages[1:]:
            role = "user" if m["role"] == "user" else "assistant"
            tag = "<|user|>" if role == "user" else "<|assistant|>"
            text += f"{tag}\n{m['content']}</s>\n"

    return {"text": text}


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════╗
║   Hancock CPU Fine-Tune — CyberViser                    ║
║   Model: TinyLlama-1.1B-Chat                            ║
║   Backend: PyTorch CPU + LoRA (PEFT)                    ║
╚══════════════════════════════════════════════════════════╝""")


def main():
    args = parse_args()

    if args.test:
        run_test()
        return

    if args.debug:
        args.max_steps = 10
        args.max_samples = 50
        print("[debug] Debug mode: 10 steps, 50 samples")

    # Override global MAX_SEQ_LEN with CLI arg
    global MAX_SEQ_LEN
    MAX_SEQ_LEN = args.max_seq_len

    # Override dataset path if specified
    global DATASET_PATH
    if args.dataset:
        DATASET_PATH = Path(args.dataset)

    print_banner()

    # ── Imports ────────────────────────────────────────────────────────────────
    print("\n[1/6] Loading libraries...")
    try:
        import torch
        from transformers import (
            AutoTokenizer,
            AutoModelForCausalLM,
            EarlyStoppingCallback,
            BitsAndBytesConfig,
        )
        from peft import LoraConfig, get_peft_model, TaskType
        from trl import SFTTrainer, SFTConfig
    except ImportError as exc:
        sys.exit(f"{FINETUNE_DEPS_HINT}\nOriginal error: {exc}")
    # ── Dataset ────────────────────────────────────────────────────────────────
    print("\n[2/6] Loading dataset...")
    if not DATASET_PATH.exists():
        sys.exit(f"ERROR: Dataset not found at {DATASET_PATH}\nRun: python hancock_pipeline.py")

    dataset = load_dataset(DATASET_PATH, max_samples=args.max_samples, debug=args.debug)

    # ── Tokenizer ──────────────────────────────────────────────────────────────
    print(f"\n[3/6] Loading tokenizer: {MODEL_NAME}")
    print("      (first run downloads ~500MB — subsequent runs use cache)")
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        revision=MODEL_REVISION,
    )
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # Format + tokenize
    dataset = dataset.map(lambda s: format_sample(s, tokenizer), remove_columns=["messages"])

    # Filter out samples that exceed max_seq_len
    def length_ok(sample):
        return len(tokenizer.encode(sample["text"])) <= MAX_SEQ_LEN

    before = len(dataset)
    dataset = dataset.filter(length_ok)
    print(f"      Samples: {before:,} → {len(dataset):,} (after length filter @ {MAX_SEQ_LEN} tokens)")

    split          = dataset.train_test_split(test_size=0.05, seed=42)
    train_dataset  = split["train"]
    eval_dataset   = split["test"]
    print(f"      Train: {len(train_dataset):,} | Eval: {len(eval_dataset):,}")

    # ── Model (CPU-Optimized 8-bit QLoRA) ──────────────────────────────────────
    print(f"\n[4/6] Loading model: {MODEL_NAME} (8-bit quantized, CPU)")
    print("      (first run downloads ~2.2GB — subsequent runs use cache)")
    t0 = time.time()

    quant_config = BitsAndBytesConfig(
        load_in_8bit=True,              # CPU-safe 8-bit quantization
        llm_int8_threshold=6.0,
        llm_int8_skip_modules=['lm_head']
    )

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        revision=MODEL_REVISION,
        quantization_config=quant_config,   # ← QLoRA enabled
        device_map='cpu',
        torch_dtype=torch.float32,
        low_cpu_mem_usage=True,
    )
    print(f"      Loaded in {time.time()-t0:.1f}s | Params: {sum(p.numel() for p in model.parameters()):,}")
    
    # ── LoRA ───────────────────────────────────────────────────────────────────
    print(f"\n[5/6] Applying LoRA (r={args.lora_r}, alpha={args.lora_r * 2})...")
    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_r * 2,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, lora_config)
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total     = sum(p.numel() for p in model.parameters())
    print(f"      Trainable: {trainable:,} / {total:,} ({100*trainable/total:.2f}%)")

    # ── Train ──────────────────────────────────────────────────────────────────
    print(f"\n[6/6] Training — {args.max_steps} steps | patience={args.patience}")
    print(f"      Effective batch: {args.batch_size * args.grad_accum}")
    print(f"      Tip: each step ~10-30s on CPU — grab a coffee ☕\n")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Write metrics to a separate CSV so they survive tqdm overwrite
    metrics_csv = OUTPUT_DIR / "training_metrics.csv"
    import csv

    class MetricsLogger:
        def __init__(self, path):
            self.path = path
            self._header_written = False
        def on_log(self, args, state, control, logs=None, **kwargs):
            if not logs:
                return
            with open(self.path, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(logs.keys()))
                if not self._header_written:
                    writer.writeheader()
                    self._header_written = True
                writer.writerow(logs)

    from transformers import TrainerCallback
    class MetricsLoggerCallback(TrainerCallback, MetricsLogger):
        def __init__(self, path):
            MetricsLogger.__init__(self, path)

    sft_config = SFTConfig(
        output_dir=str(OUTPUT_DIR),
        max_steps=args.max_steps,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        warmup_steps=max(5, args.max_steps // 20),
        learning_rate=2e-4,
        lr_scheduler_type="cosine",
        weight_decay=0.01,
        logging_steps=5 if args.debug else 10,
        eval_strategy="steps",
        eval_steps=10 if args.debug else 50,
        save_strategy="steps",
        save_steps=10 if args.debug else 50,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        report_to="none",
        run_name="hancock-cpu-v1",
        dataset_text_field="text",
        max_length=MAX_SEQ_LEN,
        fp16=False,
        bf16=False,
        dataloader_num_workers=0,
        use_cpu=True,
    )

    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        args=sft_config,
        callbacks=[
            EarlyStoppingCallback(early_stopping_patience=args.patience),
            MetricsLoggerCallback(metrics_csv),
        ],
    )

    t_start = time.time()
    trainer.train()
    elapsed = time.time() - t_start

    # ── Eval ───────────────────────────────────────────────────────────────────
    metrics = trainer.evaluate()
    eval_loss = metrics.get("eval_loss", float("nan"))
    perplexity = 2 ** eval_loss

    # ── Save ───────────────────────────────────────────────────────────────────
    model.save_pretrained(str(OUTPUT_DIR))
    tokenizer.save_pretrained(str(OUTPUT_DIR))

    # ── Optional HuggingFace push ───────────────────────────────────────────────
    if getattr(args, "hf_push", None):
        try:
            print(f"\n[hf] Pushing adapter to HuggingFace: {args.hf_push} ...")
            model.push_to_hub(args.hf_push)
            tokenizer.push_to_hub(args.hf_push)
            print(f"[hf] ✅ Pushed → https://huggingface.co/{args.hf_push}")
        except Exception as e:
            print(f"[hf] ⚠️  Push failed (non-fatal): {e}")

    # ── Summary ────────────────────────────────────────────────────────────────
    m, s = divmod(int(elapsed), 60)
    h, m = divmod(m, 60)
    print(f"""
╔══════════════════════════════════════════════════════════╗
║  ✅  Hancock CPU adapter saved!                          ║
╠══════════════════════════════════════════════════════════╣
║  📁  {str(OUTPUT_DIR):<52}║
║  ⏱   Training time : {f"{h}h {m}m {s}s":<34}║
║  📉  Eval loss     : {eval_loss:<34.4f}║
║  📊  Perplexity    : {perplexity:<34.2f}║
╠══════════════════════════════════════════════════════════╣
║  Next steps:                                             ║
║  1. Test: python hancock_cpu_finetune.py --test          ║
║  2. For Mistral 7B: use hancock_colab_finetune.ipynb     ║
╚══════════════════════════════════════════════════════════╝""")


# ── Quick inference test ────────────────────────────────────────────────────────
def run_test():
    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
        from peft import PeftModel
    except ImportError as exc:
        sys.exit(f"{FINETUNE_DEPS_HINT}\nOriginal error: {exc}")

    print("\n[test] Loading Hancock CPU adapter...")
    if not OUTPUT_DIR.exists():
        sys.exit(f"ERROR: No adapter at {OUTPUT_DIR}. Run fine-tune first.")

    base_model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        revision=MODEL_REVISION,
        torch_dtype=torch.float32,
    )
    tokenizer  = AutoTokenizer.from_pretrained(OUTPUT_DIR)  # nosec B615
    model      = PeftModel.from_pretrained(base_model, str(OUTPUT_DIR))
    model.eval()

    questions = [
        "How do I perform Kerberoasting on an authorized AD environment?",
        "What nmap flags should I use for a full port scan with service detection?",
        "How do I triage a PowerShell execution alert in Splunk?",
    ]

    pipe = pipeline("text-generation", model=model, tokenizer=tokenizer,
                    max_new_tokens=300, do_sample=True, temperature=0.7)

    for q in questions:
        prompt = f"<|system|>\n{HANCOCK_SYSTEM}</s>\n<|user|>\n{q}</s>\n<|assistant|>\n"
        print(f"\n\033[1;34m[You]\033[0m {q}")
        print("\033[1;32m[Hancock]\033[0m ", end="", flush=True)
        result = pipe(prompt)[0]["generated_text"]
        # Strip the prompt from output
        response = result[len(prompt):].strip()
        print(response[:800])
        print()


if __name__ == "__main__":
    main()

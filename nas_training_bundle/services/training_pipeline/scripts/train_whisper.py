import argparse
import json

from training_pipeline.trainer import TrainingConfig, train_whisper


def optional_positive_float(value: float | None) -> float | None:
    if value is None or value <= 0:
        return None
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name-or-path", default="openai/whisper-small")
    parser.add_argument("--train-manifest", required=True)
    parser.add_argument("--valid-manifest", required=True)
    parser.add_argument("--test-manifest")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--language", default="korean")
    parser.add_argument("--task", default="transcribe")
    parser.add_argument("--learning-rate", type=float, default=1e-5)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--eval-batch-size", type=int, default=4)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=1)
    parser.add_argument("--warmup-steps", type=int, default=0)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--logging-steps", type=int, default=10)
    parser.add_argument("--save-total-limit", type=int, default=2)
    parser.add_argument("--generation-max-length", type=int, default=256)
    parser.add_argument("--train-strategy", default="lora-encoder", choices=["full", "encoder-only", "lora", "lora-encoder"])
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument("--lora-adapter-path")
    parser.add_argument("--max-train-samples", type=int)
    parser.add_argument("--max-eval-samples", type=int)
    parser.add_argument("--min-audio-seconds", type=float, default=0.3)
    parser.add_argument("--max-audio-seconds", type=float, default=30.0)
    parser.add_argument("--max-label-tokens", type=int)
    parser.add_argument("--dataloader-num-workers", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--report-to", default="none")
    parser.add_argument("--resume-from-checkpoint")
    parser.add_argument("--fp16", action="store_true")
    parser.add_argument("--bf16", action="store_true")
    parser.add_argument("--disable-gradient-checkpointing", action="store_true")
    args = parser.parse_args()

    config = TrainingConfig(
        model_name_or_path=args.model_name_or_path,
        train_manifest_path=args.train_manifest,
        valid_manifest_path=args.valid_manifest,
        test_manifest_path=args.test_manifest,
        output_dir=args.output_dir,
        language=args.language,
        task=args.task,
        learning_rate=args.learning_rate,
        batch_size=args.batch_size,
        eval_batch_size=args.eval_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        warmup_steps=args.warmup_steps,
        num_train_epochs=args.epochs,
        weight_decay=args.weight_decay,
        logging_steps=args.logging_steps,
        save_total_limit=args.save_total_limit,
        generation_max_length=args.generation_max_length,
        train_strategy=args.train_strategy,
        lora_r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        lora_adapter_path=args.lora_adapter_path,
        max_train_samples=args.max_train_samples,
        max_eval_samples=args.max_eval_samples,
        min_audio_seconds=optional_positive_float(args.min_audio_seconds),
        max_audio_seconds=optional_positive_float(args.max_audio_seconds),
        max_label_tokens=args.max_label_tokens,
        gradient_checkpointing=not args.disable_gradient_checkpointing,
        use_fp16=args.fp16,
        use_bf16=args.bf16,
        dataloader_num_workers=args.dataloader_num_workers,
        seed=args.seed,
        report_to=args.report_to,
        resume_from_checkpoint=args.resume_from_checkpoint,
    )
    result = train_whisper(config)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

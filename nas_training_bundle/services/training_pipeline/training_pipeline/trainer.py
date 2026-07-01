from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class TrainingConfig:
    model_name_or_path: str
    train_manifest_path: str
    valid_manifest_path: str
    output_dir: str
    test_manifest_path: str | None = None
    language: str = "korean"
    task: str = "transcribe"
    learning_rate: float = 1e-5
    batch_size: int = 4
    eval_batch_size: int = 4
    gradient_accumulation_steps: int = 1
    warmup_steps: int = 0
    num_train_epochs: int = 3
    weight_decay: float = 0.01
    logging_steps: int = 10
    save_total_limit: int = 2
    generation_max_length: int = 256
    train_strategy: str = "lora-encoder"
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    lora_adapter_path: str | None = None
    max_train_samples: int | None = None
    max_eval_samples: int | None = None
    max_audio_seconds: float | None = 30.0
    min_audio_seconds: float | None = 0.3
    max_label_tokens: int | None = None
    gradient_checkpointing: bool = True
    use_fp16: bool = False
    use_bf16: bool = False
    dataloader_num_workers: int = 0
    seed: int = 42
    report_to: str = "none"
    resume_from_checkpoint: str | None = None


@dataclass
class DataCollatorSpeechSeq2SeqWithPadding:
    processor: Any
    decoder_start_token_id: int

    def __call__(self, features: list[dict[str, Any]]) -> dict[str, Any]:
        input_features = [{"input_features": feature["input_features"]} for feature in features]
        batch = self.processor.feature_extractor.pad(input_features, return_tensors="pt")

        label_features = [{"input_ids": feature["labels"]} for feature in features]
        labels_batch = self.processor.tokenizer.pad(label_features, return_tensors="pt")
        labels = labels_batch["input_ids"].masked_fill(labels_batch.attention_mask.ne(1), -100)
        if (labels[:, 0] == self.decoder_start_token_id).all().cpu().item():
            labels = labels[:, 1:]
        batch["labels"] = labels
        return batch


def _ensure_training_dependencies() -> None:
    try:
        import datasets  # noqa: F401
        import jiwer  # noqa: F401
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "Training dependencies are missing. Install services/training_pipeline/requirements.txt first."
        ) from exc


def _normalize_eval_text(text: str) -> str:
    return " ".join(text.strip().split())


def _collect_lora_target_modules(model: Any, *, encoder_only: bool) -> list[str]:
    import torch.nn as nn

    target_modules: list[str] = []
    valid_suffixes = ("q_proj", "k_proj", "v_proj", "out_proj", "fc1", "fc2")
    for name, module in model.named_modules():
        if not isinstance(module, nn.Linear):
            continue
        if encoder_only and "model.encoder" not in name:
            continue
        if name.endswith(valid_suffixes):
            target_modules.append(name)
    return sorted(set(target_modules))


def _apply_training_strategy(model: Any, config: TrainingConfig) -> Any:
    strategy = config.train_strategy.lower()

    if config.lora_adapter_path:
        try:
            from peft import PeftModel
        except ImportError as exc:
            raise RuntimeError("PEFT is required to load a LoRA adapter. Install peft in the training environment.") from exc

        return PeftModel.from_pretrained(model, config.lora_adapter_path, is_trainable=True)

    if strategy == "full":
        return model

    if strategy == "encoder-only":
        for name, parameter in model.named_parameters():
            parameter.requires_grad = name.startswith("model.encoder")
        return model

    if strategy in {"lora", "lora-encoder"}:
        try:
            from peft import LoraConfig, get_peft_model
        except ImportError as exc:
            raise RuntimeError("PEFT is required for LoRA training. Install peft in the training environment.") from exc

        target_modules = _collect_lora_target_modules(model, encoder_only=(strategy == "lora-encoder"))
        if not target_modules:
            raise RuntimeError("No target modules were found for LoRA adaptation")

        lora_config = LoraConfig(
            inference_mode=False,
            r=config.lora_r,
            lora_alpha=config.lora_alpha,
            lora_dropout=config.lora_dropout,
            bias="none",
            target_modules=target_modules,
        )
        return get_peft_model(model, lora_config)

    raise ValueError(f"Unsupported train strategy: {config.train_strategy}")


def _count_parameters(model: Any) -> tuple[int, int]:
    total_params = sum(parameter.numel() for parameter in model.parameters())
    trainable_params = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
    return trainable_params, total_params


def _enable_checkpoint_input_grads(model: Any) -> None:
    if hasattr(model, "enable_input_require_grads"):
        model.enable_input_require_grads()

    # Whisper encoder LoRA can otherwise see frozen convolution outputs with no
    # grad history when gradient checkpointing is enabled.
    encoder = None
    for path in (
        ("model", "encoder"),
        ("base_model", "model", "model", "encoder"),
        ("base_model", "model", "encoder"),
    ):
        current = model
        for attr in path:
            current = getattr(current, attr, None)
            if current is None:
                break
        if current is not None:
            encoder = current
            break

    if encoder is None:
        return

    for conv_name in ("conv1", "conv2"):
        conv_layer = getattr(encoder, conv_name, None)
        if conv_layer is None:
            continue

        def make_output_require_grad(_module: Any, _inputs: Any, output: Any) -> Any:
            output.requires_grad_(True)
            return output

        conv_layer.register_forward_hook(make_output_require_grad)
        break


def _load_manifest_dataset(
    manifest_path: str,
    *,
    processor: Any,
    max_samples: int | None,
    min_audio_seconds: float | None,
    max_audio_seconds: float | None,
    max_label_tokens: int | None,
) -> Any:
    from datasets import Audio, load_dataset

    dataset = load_dataset("json", data_files=manifest_path, split="train")
    if len(dataset) == 0:
        raise ValueError(f"Manifest has no records: {manifest_path}")

    dataset = dataset.filter(lambda item: bool(item.get("text")) and bool(item.get("audio_path")))

    if max_label_tokens is not None:
        before_count = len(dataset)

        def is_label_length_ok(item: dict[str, Any]) -> bool:
            token_ids = processor.tokenizer(item["text"], add_special_tokens=True).input_ids
            return len(token_ids) <= max_label_tokens

        dataset = dataset.filter(is_label_length_ok)
        skipped_count = before_count - len(dataset)
        if skipped_count:
            print(f"filtered {skipped_count} records over {max_label_tokens} label tokens from {manifest_path}")
        if len(dataset) == 0:
            raise ValueError(f"No records remain after label length filtering: {manifest_path}")

    if "duration_sec" in dataset.column_names:
        if min_audio_seconds is not None:
            dataset = dataset.filter(lambda item: item.get("duration_sec") is None or item["duration_sec"] >= min_audio_seconds)
        if max_audio_seconds is not None:
            dataset = dataset.filter(lambda item: item.get("duration_sec") is None or item["duration_sec"] <= max_audio_seconds)

    if max_samples is not None and len(dataset) > max_samples:
        dataset = dataset.select(range(max_samples))

    dataset = dataset.rename_column("audio_path", "audio")
    dataset = dataset.cast_column("audio", Audio(sampling_rate=16000))
    source_columns = dataset.column_names

    def prepare_batch(batch: dict[str, Any]) -> dict[str, Any]:
        audio = batch["audio"]
        batch["input_features"] = processor.feature_extractor(
            audio["array"],
            sampling_rate=audio["sampling_rate"],
        ).input_features[0]
        batch["labels"] = processor.tokenizer(batch["text"]).input_ids
        return batch

    return dataset.map(prepare_batch, remove_columns=source_columns)


def _build_compute_metrics(processor: Any):
    from jiwer import cer, wer

    def compute_metrics(pred: Any) -> dict[str, float]:
        prediction_ids = pred.predictions[0] if isinstance(pred.predictions, tuple) else pred.predictions
        label_ids = pred.label_ids.copy()
        label_ids[label_ids == -100] = processor.tokenizer.pad_token_id

        prediction_texts = processor.tokenizer.batch_decode(prediction_ids, skip_special_tokens=True)
        label_texts = processor.tokenizer.batch_decode(label_ids, skip_special_tokens=True)

        prediction_texts = [_normalize_eval_text(text) for text in prediction_texts]
        label_texts = [_normalize_eval_text(text) for text in label_texts]

        return {
            "wer": float(wer(label_texts, prediction_texts)),
            "cer": float(cer(label_texts, prediction_texts)),
        }

    return compute_metrics


def train_whisper(config: TrainingConfig) -> dict:
    _ensure_training_dependencies()

    import torch
    from transformers import (
        Seq2SeqTrainer,
        Seq2SeqTrainingArguments,
        WhisperForConditionalGeneration,
        WhisperProcessor,
        set_seed,
    )

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    set_seed(config.seed)

    processor = WhisperProcessor.from_pretrained(config.model_name_or_path)
    processor.tokenizer.set_prefix_tokens(language=config.language, task=config.task)

    model = WhisperForConditionalGeneration.from_pretrained(config.model_name_or_path)
    model.generation_config.forced_decoder_ids = processor.tokenizer.get_decoder_prompt_ids(
        language=config.language,
        task=config.task,
    )
    model.generation_config.language = config.language
    model.generation_config.task = config.task
    model.generation_config.max_length = config.generation_max_length
    model.config.use_cache = not config.gradient_checkpointing

    model = _apply_training_strategy(model, config)
    trainable_params, total_params = _count_parameters(model)
    if trainable_params == 0:
        raise RuntimeError("No trainable parameters were found. Check train_strategy or LoRA adapter settings.")
    print(f"trainable parameters: {trainable_params:,} / {total_params:,}")

    if config.gradient_checkpointing:
        if hasattr(model, "gradient_checkpointing_enable"):
            model.gradient_checkpointing_enable()
        _enable_checkpoint_input_grads(model)

    train_dataset = _load_manifest_dataset(
        config.train_manifest_path,
        processor=processor,
        max_samples=config.max_train_samples,
        min_audio_seconds=config.min_audio_seconds,
        max_audio_seconds=config.max_audio_seconds,
        max_label_tokens=config.max_label_tokens or getattr(model.config, "max_target_positions", 448),
    )
    valid_dataset = _load_manifest_dataset(
        config.valid_manifest_path,
        processor=processor,
        max_samples=config.max_eval_samples,
        min_audio_seconds=config.min_audio_seconds,
        max_audio_seconds=config.max_audio_seconds,
        max_label_tokens=config.max_label_tokens or getattr(model.config, "max_target_positions", 448),
    )
    test_dataset = None
    if config.test_manifest_path:
        test_dataset = _load_manifest_dataset(
            config.test_manifest_path,
            processor=processor,
            max_samples=config.max_eval_samples,
            min_audio_seconds=config.min_audio_seconds,
            max_audio_seconds=config.max_audio_seconds,
            max_label_tokens=config.max_label_tokens or getattr(model.config, "max_target_positions", 448),
        )

    collator = DataCollatorSpeechSeq2SeqWithPadding(
        processor=processor,
        decoder_start_token_id=model.config.decoder_start_token_id,
    )

    report_to = [] if config.report_to == "none" else [config.report_to]
    training_args = Seq2SeqTrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=config.batch_size,
        per_device_eval_batch_size=config.eval_batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        learning_rate=config.learning_rate,
        warmup_steps=config.warmup_steps,
        num_train_epochs=config.num_train_epochs,
        weight_decay=config.weight_decay,
        logging_steps=config.logging_steps,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        predict_with_generate=True,
        generation_max_length=config.generation_max_length,
        save_total_limit=config.save_total_limit,
        load_best_model_at_end=True,
        metric_for_best_model="cer",
        greater_is_better=False,
        fp16=config.use_fp16,
        bf16=config.use_bf16,
        dataloader_num_workers=config.dataloader_num_workers,
        remove_unused_columns=False,
        label_names=["labels"],
        report_to=report_to,
        gradient_checkpointing=config.gradient_checkpointing,
        optim="adamw_torch",
    )

    trainer = Seq2SeqTrainer(
        args=training_args,
        model=model,
        train_dataset=train_dataset,
        eval_dataset=valid_dataset,
        data_collator=collator,
        tokenizer=processor.feature_extractor,
        compute_metrics=_build_compute_metrics(processor),
    )

    train_result = trainer.train(resume_from_checkpoint=config.resume_from_checkpoint)
    trainer.save_model(str(output_dir))
    processor.save_pretrained(str(output_dir))

    eval_metrics = trainer.evaluate(metric_key_prefix="eval")
    test_metrics = trainer.evaluate(eval_dataset=test_dataset, metric_key_prefix="test") if test_dataset is not None else {}

    result = {
        "status": "trained",
        "config": asdict(config),
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "train_samples": len(train_dataset),
        "valid_samples": len(valid_dataset),
        "test_samples": len(test_dataset) if test_dataset is not None else 0,
        "train_runtime": float(train_result.metrics.get("train_runtime", 0.0)),
        "train_loss": float(train_result.metrics.get("train_loss", 0.0)),
        "trainable_params": trainable_params,
        "total_params": total_params,
        "eval_metrics": {key: float(value) for key, value in eval_metrics.items() if isinstance(value, (int, float))},
        "test_metrics": {key: float(value) for key, value in test_metrics.items() if isinstance(value, (int, float))},
    }

    (output_dir / "training_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result

# Last reviewed: 2025-04-29 08:12:26 UTC (User: TeeksssPre-trained)
from typing import List, Dict, Any, Optional, Union, Tuple
import os
import torch
import json
import time
import logging
import asyncio
from pydantic import BaseModel

from ..utils.config import (
    FINE_TUNING_MODEL_BASE,
    FINE_TUNING_OUTPUT_DIR,
    FINE_TUNING_EPOCHS,
    FINE_TUNING_BATCH_SIZE,
    FINE_TUNING_LEARNING_RATE,
    FINE_TUNING_MAX_LENGTH,
    FINE_TUNING_GRADIENT_ACCUMULATION_STEPS
)
from ..utils.logger import get_logger
from ..websockets.background_tasks import manager as task_manager

logger = get_logger(__name__)

# Lazy imports
transformers = None
datasets = None
torch_xla = None

class FineTuningConfig(BaseModel):
    model_name: str
    output_dir: str
    epochs: int = 3
    batch_size: int = 8
    learning_rate: float = 3e-5
    max_length: int = 512
    gradient_accumulation_steps: int = 4
    use_peft: bool = False
    use_lora: bool = False
    lora_rank: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.05
    use_8bit: bool = False
    use_4bit: bool = False
    device: str = "auto"
    fp16: bool = True
    evaluation_strategy: str = "steps"
    eval_steps: int = 500
    save_steps: int = 1000
    warmup_steps: int = 100
    logging_steps: int = 100
    save_total_limit: int = 3
    load_best_model_at_end: bool = True
    metric_for_best_model: str = "eval_loss"
    greater_is_better: bool = False

class TrainingExample(BaseModel):
    question: str
    context: Optional[str] = None
    answer: str

class FineTuningManager:
    def __init__(self):
        self.is_initialized = False
        self._import_libraries()
    
    def _import_libraries(self):
        """Kütüphaneleri gerektiğinde import et"""
        global transformers, datasets, torch_xla
        
        if self.is_initialized:
            return
            
        try:
            import transformers
            import datasets
            
            try:
                import torch_xla
                import torch_xla.core.xla_model as xm
                self.tpu_available = True
            except ImportError:
                self.tpu_available = False
                
            self.is_initialized = True
            logger.info("Fine-tuning libraries loaded successfully")
        except ImportError as e:
            logger.error(f"Failed to import fine-tuning libraries: {e}")
            raise
    
    def prepare_dataset(self, examples: List[TrainingExample], config: FineTuningConfig) -> Tuple[Any, Any]:
        """Eğitim verilerini hazırlar"""
        self._import_libraries()
        
        # Model ailesine göre veri formatını belirle
        is_encoder_decoder = "t5" in config.model_name.lower()
        is_causal_lm = any(name in config.model_name.lower() for name in ["gpt", "llama", "mistral"])
        
        # Tokenizer'ı yükle
        tokenizer = transformers.AutoTokenizer.from_pretrained(config.model_name)
        
        if is_causal_lm and not tokenizer.pad_token:
            tokenizer.pad_token = tokenizer.eos_token
        
        # Veriler için liste hazırla
        train_data = []
        
        if is_encoder_decoder:  # T5 format
            for example in examples:
                context = example.context if example.context else ""
                question = example.question
                answer = example.answer
                
                input_text = f"question: {question} context: {context}"
                target_text = answer
                
                train_data.append({
                    "input_text": input_text,
                    "target_text": target_text
                })
                
        elif is_causal_lm:  # GPT/LLaMA format
            for example in examples:
                context = example.context if example.context else ""
                question = example.question
                answer = example.answer
                
                if context:
                    prompt = f"Context: {context}\n\nQuestion: {question}\n\nAnswer:"
                else:
                    prompt = f"Question: {question}\n\nAnswer:"
                
                train_data.append({
                    "prompt": prompt,
                    "completion": answer
                })
        
        # Dataset oluştur
        dataset = datasets.Dataset.from_dict({
            key: [item[key] for item in train_data] 
            for key in train_data[0].keys()
        })
        
        # Train/test split
        dataset = dataset.train_test_split(test_size=0.1, seed=42)
        
        # Tokenization fonksiyonu
        def tokenize_function(examples):
            if is_encoder_decoder:
                model_inputs = tokenizer(
                    examples["input_text"],
                    max_length=config.max_length,
                    padding="max_length",
                    truncation=True
                )
                
                labels = tokenizer(
                    examples["target_text"],
                    max_length=config.max_length,
                    padding="max_length",
                    truncation=True
                )
                
                model_inputs["labels"] = labels["input_ids"]
                return model_inputs
            
            elif is_causal_lm:
                # Causal LM için prompt + completion birleştirilir
                texts = []
                for prompt, completion in zip(examples["prompt"], examples["completion"]):
                    texts.append(f"{prompt} {completion}{tokenizer.eos_token}")
                
                model_inputs = tokenizer(
                    texts,
                    max_length=config.max_length,
                    padding="max_length",
                    truncation=True
                )
                
                # Attention mask kullanarak labels oluştur - sadece completion kısmını tahmin et
                labels = []
                for i, (prompt, completion) in enumerate(zip(examples["prompt"], examples["completion"])):
                    prompt_len = len(tokenizer(prompt)["input_ids"])
                    input_len = len(model_inputs["input_ids"][i])
                    
                    # Completion'a karşılık gelen kısım için loss hesapla, prompt için -100 (ignore)
                    label = [-100] * prompt_len  # Prompt için -100
                    label.extend(model_inputs["input_ids"][i][prompt_len:])  # Completion için gerçek token ID'leri
                    
                    # Uzunluğu max_length'e eşitle
                    if len(label) < config.max_length:
                        label.extend([-100] * (config.max_length - len(label)))
                    else:
                        label = label[:config.max_length]
                        
                    labels.append(label)
                
                model_inputs["labels"] = labels
                return model_inputs
                
        # Dataset'i tokenize et
        tokenized_datasets = dataset.map(
            tokenize_function,
            batched=True,
            remove_columns=dataset["train"].column_names
        )
        
        return tokenized_datasets, tokenizer
    
    async def fine_tune(self, examples: List[TrainingExample], config: Optional[FineTuningConfig] = None, task_id: str = None, user_id: int = None) -> str:
        """Fine-tuning işlemini başlatır"""
        self._import_libraries()
        
        # Yapılandırma varsayılanları
        if config is None:
            config = FineTuningConfig(
                model_name=FINE_TUNING_MODEL_BASE,
                output_dir=FINE_TUNING_OUTPUT_DIR,
                epochs=FINE_TUNING_EPOCHS,
                batch_size=FINE_TUNING_BATCH_SIZE,
                learning_rate=FINE_TUNING_LEARNING_RATE,
                max_length=FINE_TUNING_MAX_LENGTH,
                gradient_accumulation_steps=FINE_TUNING_GRADIENT_ACCUMULATION_STEPS
            )
        
        # Çıktı dizinini oluştur
        os.makedirs(config.output_dir, exist_ok=True)
        
        # Task güncellemesi
        if task_id:
            await task_manager.update_task(task_id, progress=10, status="running")
        
        try:
            # Dataset ve tokenizer hazırla
            dataset_future = asyncio.to_thread(self.prepare_dataset, examples, config)
            tokenized_datasets, tokenizer = await dataset_future
            
            # Task güncellemesi
            if task_id:
                await task_manager.update_task(task_id, progress=20, status="running")
            
            # Model seçimi ve yapılandırma
            model_config_dict = {
                "trust_remote_code": True
            }
            
            # Quantization seçeneği
            if config.use_8bit:
                from transformers import BitsAndBytesConfig
                model_config_dict["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)
            elif config.use_4bit:
                from transformers import BitsAndBytesConfig
                model_config_dict["quantization_config"] = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True
                )
            
            # Cihaz seçimi
            if config.device == "auto":
                config.device = "cuda" if torch.cuda.is_available() else "cpu"
                if self.tpu_available:
                    config.device = "tpu"
            
            if config.device == "cuda":
                model_config_dict["device_map"] = "auto"
                model_config_dict["torch_dtype"] = torch.float16 if config.fp16 else torch.float32
            
            # Task güncellemesi
            if task_id:
                await task_manager.update_task(task_id, progress=30, status="running")
            
            # Model yükleme
            def load_model_sync():
                if "t5" in config.model_name.lower():
                    logger.info(f"Loading T5 model: {config.model_name}")
                    model = transformers.T5ForConditionalGeneration.from_pretrained(
                        config.model_name, **model_config_dict
                    )
                else:
                    logger.info(f"Loading Causal LM model: {config.model_name}")
                    model = transformers.AutoModelForCausalLM.from_pretrained(
                        config.model_name, **model_config_dict
                    )
                return model
            
            # Model yükleme (CPU-bound işlem)
            model = await asyncio.to_thread(load_model_sync)
            
            # Task güncellemesi
            if task_id:
                await task_manager.update_task(task_id, progress=40, status="running")
            
            # PEFT/LoRA desteği (parametrik etkin ince ayarlama)
            if config.use_peft and config.use_lora:
                from peft import prepare_model_for_int8_training, LoraConfig, get_peft_model
                
                # Int8 modeli hazırla
                if config.use_8bit:
                    model = prepare_model_for_int8_training(model)
                
                # LoRA konfigürasyonu
                lora_config = LoraConfig(
                    r=config.lora_rank,
                    lora_alpha=config.lora_alpha,
                    target_modules=["q_proj", "v_proj"],
                    lora_dropout=config.lora_dropout,
                    bias="none",
                    task_type="CAUSAL_LM" if "t5" not in config.model_name.lower() else "SEQ_2_SEQ_LM"
                )
                
                # LoRA modelini hazırla
                model = get_peft_model(model, lora_config)
                model.print_trainable_parameters()
            
            # Task güncellemesi
            if task_id:
                await task_manager.update_task(task_id, progress=50, status="running")
            
            # Training arguments
            training_args = transformers.TrainingArguments(
                output_dir=config.output_dir,
                num_train_epochs=config.epochs,
                per_device_train_batch_size=config.batch_size,
                per_device_eval_batch_size=config.batch_size,
                gradient_accumulation_steps=config.gradient_accumulation_steps,
                learning_rate=config.learning_rate,
                weight_decay=0.01,
                warmup_steps=config.warmup_steps,
                evaluation_strategy=config.evaluation_strategy,
                eval_steps=config.eval_steps,
                save_steps=config.save_steps,
                logging_steps=config.logging_steps,
                save_total_limit=config.save_total_limit,
                load_best_model_at_end=config.load_best_model_at_end,
                metric_for_best_model=config.metric_for_best_model,
                greater_is_better=config.greater_is_better,
                fp16=config.fp16 and config.device == "cuda",
                report_to="none",  # Wandb/TensorBoard desteği buradan eklenebilir
                push_to_hub=False
            )
            
            # TPU desteği
            if config.device == "tpu":
                import torch_xla.core.xla_model as xm
                import torch_xla.distributed.xla_multiprocessing as xmp
                
                training_args.tpu_num_cores = xm.xrt_world_size()
                # TPU için ekstra yapılandırma
                # ...
            
            # Task güncellemesi
            if task_id:
                await task_manager.update_task(task_id, progress=60, status="running")
            
            # Eğitimi başlat - callback ile ilerlemeyi takip et
            class ProgressCallback(transformers.TrainerCallback):
                def __init__(self, task_id, total_epochs, start_progress=60, end_progress=95):
                    self.task_id = task_id
                    self.total_epochs = total_epochs
                    self.start_progress = start_progress
                    self.end_progress = end_progress
                    self.progress_range = end_progress - start_progress
                
                def on_epoch_end(self, args, state, control, **kwargs):
                    current_epoch = state.epoch
                    progress = self.start_progress + int((current_epoch / self.total_epochs) * self.progress_range)
                    asyncio.create_task(task_manager.update_task(
                        self.task_id, 
                        progress=min(progress, self.end_progress),
                        status="running"
                    ))
                    logger.info(f"Training progress: {current_epoch}/{self.total_epochs} epochs")
                
                def on_log(self, args, state, control, logs=None, **kwargs):
                    if logs:
                        logger.info(f"Training logs: {json.dumps(logs)}")
            
            callbacks = []
            if task_id:
                callbacks.append(ProgressCallback(task_id, config.epochs))
                
            # Data Collator
            data_collator = transformers.DataCollatorForSeq2Seq(
                tokenizer=tokenizer,
                model=model,
            )
            
            # Trainer oluştur
            trainer = transformers.Trainer(
                model=model,
                args=training_args,
                train_dataset=tokenized_datasets["train"],
                eval_dataset=tokenized_datasets["test"],
                data_collator=data_collator,
                tokenizer=tokenizer,
                callbacks=callbacks
            )
            
            # Trainer'ı başlat
            await asyncio.to_thread(trainer.train)
            
            # En iyi modeli kaydet
            await asyncio.to_thread(trainer.save_model, config.output_dir)
            tokenizer.save_pretrained(config.output_dir)
            
            # Task güncellemesi
            if task_id:
                metrics = trainer.evaluate()
                await task_manager.update_task(
                    task_id, 
                    progress=100, 
                    status="completed",
                    result={
                        "model_path": config.output_dir,
                        "metrics": metrics,
                        "num_examples": len(examples)
                    }
                )
            
            logger.info(f"Fine-tuning completed successfully, model saved to {config.output_dir}")
            return config.output_dir
            
        except Exception as e:
            logger.error(f"Fine-tuning error: {e}", exc_info=True)
            
            # Task hatası
            if task_id:
                await task_manager.update_task(task_id, status="failed", error=str(e))
            
            raise

# Fine-tuning manager singleton
fine_tuning_manager = FineTuningManager()
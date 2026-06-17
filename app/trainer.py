import os
import pandas as pd
import torch
from transformers import (
    AutoTokenizer, 
    AutoModelForMaskedLM, 
    DataCollatorForLanguageModeling, 
    Trainer, 
    TrainingArguments
)
from datasets import Dataset

DATA_DIR = "data"
MODEL_NAME = "emilyalsentzer/Bio_ClinicalBERT"
OUTPUT_DIR = os.path.join("app", "model_weights")

def train_model():
    print("--- Starting Clinical BERT Fine-tuning ---")
    
    # 1. Load Data from multiple sources to maximize dataset size
    texts = []
    
    # Source A: Notes (if populated)
    notes_path = os.path.join(DATA_DIR, "NOTEEVENTS.csv")
    if os.path.exists(notes_path):
        df_notes = pd.read_csv(notes_path)
        if "text" in df_notes.columns:
            texts.extend(df_notes["text"].dropna().astype(str).tolist())
        elif "TEXT" in df_notes.columns:
            texts.extend(df_notes["TEXT"].dropna().astype(str).tolist())
            
    # Source B: ICD Diagnoses Dictionary (Long titles are great clinical text)
    icd_path = os.path.join(DATA_DIR, "D_ICD_DIAGNOSES.csv")
    if os.path.exists(icd_path):
        print(f"Loading clinical text from {icd_path}...")
        df_icd = pd.read_csv(icd_path)
        if "long_title" in df_icd.columns:
            texts.extend(df_icd["long_title"].dropna().astype(str).tolist())
            
    # Source C: Clinical Items Dictionary
    items_path = os.path.join(DATA_DIR, "D_ITEMS.csv")
    if os.path.exists(items_path):
        print(f"Loading clinical text from {items_path}...")
        df_items = pd.read_csv(items_path)
        if "label" in df_items.columns:
            texts.extend(df_items["label"].dropna().astype(str).tolist())

    if not texts:
        print("Error: No textual data could be found in the data/ directory.")
        return
        
    print(f"Aggregated a total of {len(texts)} text records for training.")
    
    # 2. Prepare Dataset
    dataset = Dataset.from_dict({"text": texts})
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=False)

    def tokenize_function(examples):
        return tokenizer(examples["text"], truncation=True, padding="max_length", max_length=128)

    # Ensure the columns are properly added
    tokenized_datasets = dataset.map(tokenize_function, batched=True, remove_columns=["text"])

    # 3. Initialize Model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device for training: {device}")
    model = AutoModelForMaskedLM.from_pretrained(MODEL_NAME).to(device)

    # 4. Data Collator for MLM
    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm_probability=0.15)

    # 5. Training Arguments
    training_args = TrainingArguments(
        output_dir="./temp_trainer",
        num_train_epochs=120, # Increased from 1 to 120 as requested
        per_device_train_batch_size=4, # Reduced from 4 to 1 to save VRAM
        gradient_accumulation_steps=4, # Accumulate gradients to maintain effective batch size
        save_steps=100,
        save_total_limit=1,
        fp16=True if device == "cuda" else False, # Speed up on NVIDIA GPUs
        logging_steps=10,
        remove_unused_columns=False # Prevent Trainer from dropping input_ids if names mismatch slightly
    )

    # 6. Initialize Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        data_collator=data_collator,
        train_dataset=tokenized_datasets,
    )

    # 7. Execute Training
    print("Executing training loop...")
    train_result = trainer.train()
    metrics = train_result.metrics

    # 8. Save Weights
    print(f"Saving fine-tuned weights to: {OUTPUT_DIR}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    
    # 9. Generate HTML Report
    generate_html_report(metrics)
    
    print("Training complete! The API will now use these local weights.")

def generate_html_report(metrics):
    report_path = "app/static/training_report.html"
    os.makedirs("app/static", exist_ok=True)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Training Accuracy Report</title>
        <style>
            body {{ font-family: sans-serif; padding: 20px; background: #f4f4f9; }}
            .card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            h1 {{ color: #2c3e50; }}
            .metric {{ margin: 10px 0; font-size: 1.2em; }}
            .value {{ font-weight: bold; color: #3498db; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Training Results</h1>
            <p>Report generated on: {pd.Timestamp.now()}</p>
            <div class="metric">Training Loss: <span class="value">{metrics.get('train_loss', 'N/A'):.4f}</span></div>
            <div class="metric">Training Runtime: <span class="value">{metrics.get('train_runtime', 'N/A'):.2f}s</span></div>
            <div class="metric">Samples per Second: <span class="value">{metrics.get('train_samples_per_second', 'N/A'):.2f}</span></div>
            <hr>
            <p><i>Note: For full accuracy metrics, ensure a validation dataset is provided in trainer arguments.</i></p>
            <a href="/static/index.html">Back to Dashboard</a>
        </div>
    </body>
    </html>
    """
    with open(report_path, "w") as f:
        f.write(html_content)
    print(f"Report generated at: {report_path}")

if __name__ == "__main__":
    train_model()

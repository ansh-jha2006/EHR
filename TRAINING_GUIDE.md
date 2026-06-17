# Training Guide: Clinical BERT Fine-tuning

This guide explains how to fine-tune the Clinical BERT model on your local EHR data and ensure the system uses the new weights.

## 1. Prerequisites
- **Python Environment**: Use the Linux-compatible environment created: \`venv_linux\`.
- **NVIDIA Drivers**: Ensure you have modern NVIDIA drivers installed (CUDA 12.1+ recommended). If you see "driver too old" errors, please update your drivers.

## 2. Start the Training
To begin fine-tuning the model on your local \`NOTEEVENTS.csv\` data, run:

\`\`\`bash
./venv_linux/bin/python3 -m app.trainer
\`\`\`

### What happens during training?
- **Data Loading**: It loads clinical notes from \`data/NOTEEVENTS.csv\`.
- **NVIDIA GPU Acceleration**: The script automatically detects your NVIDIA GPU and uses CUDA.
- **Weight Saving**: Once training is complete, the fine-tuned model weights and tokenizer configuration are saved to the \`app/model_weights/\` directory.


## 2. Using the Trained Weights
The system is already configured to prioritize local weights. When you start the FastAPI server:

```bash
uvicorn app.main:app --reload
```

The console will output:
`Loading LOCALLY TRAINED weights from: app/model_weights`

If this folder is deleted or not present, it will automatically fallback to the original `emilyalsentzer/Bio_ClinicalBERT` model from Hugging Face.

## 3. Verifying Results
After training, any results from the `/summarize` or `/analyze_note` endpoints will be derived from your locally-tuned model, providing more context-aware embeddings and clinical insights.

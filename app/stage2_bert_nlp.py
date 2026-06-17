import torch
from transformers import AutoTokenizer, AutoModel, pipeline
import numpy as np

import os

class BERTClinicalAnalyzer:
    def __init__(self, model_name="emilyalsentzer/Bio_ClinicalBERT"):
        # Stage 3: Prefer local trained weights if they exist and are valid
        local_weights = os.path.join("app", "model_weights")
        if os.path.exists(local_weights) and os.path.exists(os.path.join(local_weights, "config.json")):
            print(f"Loading LOCALLY TRAINED weights from: {local_weights}")
            model_path = local_weights
        else:
            print(f"Initializing BERTClinicalAnalyzer with base model: {model_name}")
            model_path = model_name

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, use_fast=False)
        self.model = AutoModel.from_pretrained(model_path).to(self.device)
        
        # Keep NER on a standard high-quality model for reliability
        self.ner_pipeline = pipeline("ner", model="dbmdz/bert-large-cased-finetuned-conll03-english", device=0 if self.device == "cuda" else -1)

    def encode_text(self, text: str):
        """Generate BERT embeddings for clinical text."""
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512, padding=True).to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)
        # Use mean pooling of the last hidden state as sentence embedding
        embeddings = outputs.last_hidden_state.mean(dim=1)
        return embeddings.numpy().tolist()[0]

    def extract_entities(self, text: str):
        """Extract medical-like entities using a BERT-based NER pipeline."""
        # This is a placeholder using a general NER model. 
        # In a real clinical setting, a specialized Med-NER model would be used.
        results = self.ner_pipeline(text)
        entities = []
        for res in results:
            if res['score'] > 0.8:
                entities.append({"word": res['word'], "entity": res['entity'], "score": float(res['score'])})
        return entities

    def summarize_text(self, text: str, num_sentences: int = 3) -> str:
        """Extractive summarization using local BERT embeddings."""
        if not text or not text.strip():
            return "No text provided."
        
        # Simple sentence splitting (could be improved with nltk)
        sentences = [s.strip() + "." for s in text.split(".") if s.strip()]
        if len(sentences) <= num_sentences:
            return text
            
        # Get embeddings for all sentences
        inputs = self.tokenizer(sentences, return_tensors="pt", truncation=True, max_length=512, padding=True).to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)
            
        sentence_embeddings = outputs.last_hidden_state.mean(dim=1).cpu().numpy()
        
        # Get document embedding
        doc_inputs = self.tokenizer([text], return_tensors="pt", truncation=True, max_length=512, padding=True).to(self.device)
        with torch.no_grad():
            doc_outputs = self.model(**doc_inputs)
        doc_embedding = doc_outputs.last_hidden_state.mean(dim=1).cpu().numpy()[0]
        
        # Calculate cosine similarity between each sentence and the whole document
        from numpy import dot
        from numpy.linalg import norm
        
        similarities = []
        for emb in sentence_embeddings:
            sim = dot(emb, doc_embedding)/(norm(emb)*norm(doc_embedding))
            similarities.append(sim)
            
        # Get top indices
        top_indices = np.argsort(similarities)[-num_sentences:]
        top_indices = sorted(top_indices) # Keep original order
        
        summary = " ".join([sentences[i] for i in top_indices])
        return summary


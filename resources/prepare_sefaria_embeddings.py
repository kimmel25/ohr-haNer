"""
Sefaria Embeddings Preparation Script
======================================

ONE-TIME SETUP: Run this script once to create BEREL embeddings from your Sefaria export.

This script:
1. Reads all Hebrew texts from your Sefaria export
2. Creates BEREL embeddings for each text
3. Saves embeddings and metadata to embeddings/ directory
4. Takes ~4 hours for full corpus (~50,000 texts)

After running this once, embeddings are cached forever (unless Sefaria updates).

REQUIREMENTS:
- Sefaria export downloaded (MongoDB dump or Git export)
- Python packages: transformers, torch, numpy
- 8GB+ RAM recommended
- 10GB disk space for embeddings

USAGE:
    python prepare_sefaria_embeddings.py --sefaria-path /path/to/sefaria/export
"""

import os
import json
import argparse
from pathlib import Path
from typing import List, Dict
import numpy as np
from tqdm import tqdm

# BEREL imports
try:
    from transformers import AutoTokenizer, AutoModel
    import torch
    BEREL_AVAILABLE = True
except ImportError:
    print("ERROR: BEREL dependencies not installed!")
    print("Install with: pip install transformers torch")
    BEREL_AVAILABLE = False
    exit(1)

from logging_config import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


class SefariaEmbeddingGenerator:
    """Generates BEREL embeddings for Sefaria texts"""
    
    def __init__(self, output_dir: str = "embeddings"):
        self.output_dir = Path(__file__).parent / output_dir
        self.output_dir.mkdir(exist_ok=True)
        
        logger.info("="*80)
        logger.info("SEFARIA EMBEDDING GENERATOR")
        logger.info("="*80)
        logger.info(f"Output directory: {self.output_dir}")
        
        # Load BEREL model
        logger.info("\nLoading BEREL model...")
        self.tokenizer = AutoTokenizer.from_pretrained("dicta-il/BEREL")
        self.model = AutoModel.from_pretrained("dicta-il/BEREL")
        self.model.eval()
        logger.info("✓ BEREL model loaded")
        
        # Check for GPU
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        logger.info(f"✓ Using device: {self.device}")
    
    def embed_text(self, text: str) -> np.ndarray:
        """Create BEREL embedding for a single text"""
        # Tokenize
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Get embeddings
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        # Use [CLS] token embedding
        embedding = outputs.last_hidden_state[0][0].cpu().numpy()
        
        return embedding
    
    def load_sefaria_texts(self, sefaria_path: Path) -> List[Dict]:
        """
        Load texts from Sefaria export.
        
        TODO: CONFIGURE THIS BASED ON YOUR SEFARIA EXPORT FORMAT
        
        If you have the MongoDB dump:
            - Extract with: mongorestore dump/
            - Then query: db.texts.find({})
        
        If you have the Git export:
            - Read from: json/Talmud/*.json
            
        Returns list of:
        [
            {
                'ref': 'Kesubos 12a',
                'he_text': 'Hebrew text...',
                'en_text': 'English text...',
                'category': 'Gemara'
            },
            ...
        ]
        """
        logger.info("\n" + "="*80)
        logger.info("LOADING SEFARIA TEXTS")
        logger.info("="*80)
        
        texts = []
        
        # ================================================================
        # TODO: CONFIGURE YOUR SEFARIA DATA PATH HERE
        # ================================================================
        
        # Option 1: If you have JSON files from Git export
        if (sefaria_path / "json" / "Talmud").exists():
            logger.info("Detected Git export format")
            texts = self._load_from_git_export(sefaria_path)
        
        # Option 2: If you have MongoDB dump
        elif (sefaria_path / "sefaria").exists():
            logger.info("Detected MongoDB dump format")
            texts = self._load_from_mongodb(sefaria_path)
        
        # Option 3: If you have API-downloaded JSON files
        elif (sefaria_path / "texts").exists():
            logger.info("Detected API download format")
            texts = self._load_from_api_format(sefaria_path)
        
        else:
            logger.error(f"Could not detect Sefaria format in: {sefaria_path}")
            logger.error("\nSupported formats:")
            logger.error("  1. Git export: /path/to/Sefaria-Export/json/")
            logger.error("  2. MongoDB dump: /path/to/dump/sefaria/")
            logger.error("  3. API download: /path/to/texts/")
            return []
        
        logger.info(f"\n✓ Loaded {len(texts)} texts from Sefaria")
        return texts
    
    def _load_from_git_export(self, sefaria_path: Path) -> List[Dict]:
        """
        Load from Git export format.
        
        Structure: json/Talmud/Bavli/Seder Nashim/Kesubos/Hebrew/merged.json
        """
        texts = []
        
        # TODO: Customize which sections to include
        # For now, focusing on Talmud Bavli (the most important for yeshivish queries)
        
        talmud_dir = sefaria_path / "json" / "Talmud" / "Bavli"
        
        if not talmud_dir.exists():
            logger.warning(f"Talmud directory not found: {talmud_dir}")
            return texts
        
        # Iterate through Sedarim (orders)
        for seder_dir in talmud_dir.iterdir():
            if not seder_dir.is_dir():
                continue
            
            logger.info(f"  Processing: {seder_dir.name}")
            
            # Iterate through Masechtot (tractates)
            for masechta_dir in seder_dir.iterdir():
                if not masechta_dir.is_dir():
                    continue
                
                masechta_name = masechta_dir.name
                
                # Load Hebrew text
                he_file = masechta_dir / "Hebrew" / "merged.json"
                en_file = masechta_dir / "English" / "merged.json"
                
                if he_file.exists():
                    try:
                        with open(he_file, 'r', encoding='utf-8') as f:
                            he_data = json.load(f)
                        
                        # Load English if available
                        en_data = {}
                        if en_file.exists():
                            with open(en_file, 'r', encoding='utf-8') as f:
                                en_data = json.load(f)
                        
                        # Extract texts
                        extracted = self._extract_texts_from_json(
                            masechta_name,
                            he_data,
                            en_data
                        )
                        texts.extend(extracted)
                        
                    except Exception as e:
                        logger.error(f"Error loading {masechta_name}: {e}")
        
        return texts
    
    def _load_from_mongodb(self, sefaria_path: Path) -> List[Dict]:
        """
        Load from MongoDB dump format.
        
        TODO: If using MongoDB, you'll need to:
        1. Install: pip install pymongo
        2. Start MongoDB: mongod
        3. Restore dump: mongorestore dump/
        4. Query texts from Python
        
        Example:
            from pymongo import MongoClient
            client = MongoClient()
            db = client.sefaria
            texts = list(db.texts.find({}))
        """
        logger.warning("MongoDB loading not yet implemented")
        logger.warning("You can either:")
        logger.warning("  1. Use the Git export format (json/ directory)")
        logger.warning("  2. Implement MongoDB loading here")
        logger.warning("  3. Use the API download format")
        return []
    
    def _load_from_api_format(self, sefaria_path: Path) -> List[Dict]:
        """
        Load from API-downloaded JSON format (from download_sefaria_backend.py).
        
        Structure: texts/Kesubos_12a.json
        """
        texts = []
        texts_dir = sefaria_path / "texts"
        
        if not texts_dir.exists():
            logger.warning(f"Texts directory not found: {texts_dir}")
            return texts
        
        # Load all JSON files
        json_files = list(texts_dir.glob("*.json"))
        logger.info(f"  Found {len(json_files)} JSON files")
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                ref = data.get('ref', json_file.stem)
                he_text = data.get('he_text', '')
                en_text = data.get('en_text', '')
                
                if he_text:  # Only include if there's Hebrew text
                    texts.append({
                        'ref': ref,
                        'he_text': he_text[:2000],  # Limit length
                        'en_text': en_text[:2000],
                        'category': 'Gemara'  # Default category
                    })
                    
            except Exception as e:
                logger.error(f"Error loading {json_file}: {e}")
        
        return texts
    
    def _extract_texts_from_json(
        self, 
        masechta_name: str, 
        he_data: dict, 
        en_data: dict
    ) -> List[Dict]:
        """Extract individual daf texts from merged JSON"""
        texts = []
        
        # Get the text content (handle nested structure)
        he_text = he_data.get('text', [])
        en_text = en_data.get('text', [])
        
        # If text is a list of dapim
        if isinstance(he_text, list):
            for i, daf_text in enumerate(he_text):
                if not daf_text:  # Skip empty dapim
                    continue
                
                # Flatten if nested (some texts have further nesting)
                if isinstance(daf_text, list):
                    daf_text = ' '.join(str(x) for x in daf_text if x)
                
                # Get corresponding English if available
                en_daf = ''
                if i < len(en_text):
                    en_daf = en_text[i]
                    if isinstance(en_daf, list):
                        en_daf = ' '.join(str(x) for x in en_daf if x)
                
                # Create reference (e.g., "Kesubos 2a")
                daf_num = (i // 2) + 2  # Start from 2a
                side = 'a' if i % 2 == 0 else 'b'
                ref = f"{masechta_name} {daf_num}{side}"
                
                texts.append({
                    'ref': ref,
                    'he_text': str(daf_text)[:2000],  # Limit length
                    'en_text': str(en_daf)[:2000],
                    'category': 'Gemara'
                })
        
        return texts
    
    def generate_embeddings(self, texts: List[Dict]) -> tuple:
        """
        Generate BEREL embeddings for all texts.
        
        Returns: (embeddings_array, metadata_list)
        """
        logger.info("\n" + "="*80)
        logger.info("GENERATING EMBEDDINGS")
        logger.info("="*80)
        logger.info(f"Total texts to embed: {len(texts)}")
        logger.info("This will take ~4 hours for full corpus")
        logger.info("")
        
        embeddings = []
        metadata = []
        
        # Process with progress bar
        for text in tqdm(texts, desc="Creating embeddings"):
            try:
                # Use Hebrew text for embedding (it's what we're searching for)
                he_text = text.get('he_text', '')
                if not he_text:
                    continue
                
                # Create embedding
                embedding = self.embed_text(he_text)
                embeddings.append(embedding)
                
                # Store metadata
                metadata.append({
                    'ref': text.get('ref', ''),
                    'he_text': text.get('he_text', '')[:500],  # Store snippet
                    'en_text': text.get('en_text', '')[:500],
                    'category': text.get('category', '')
                })
                
            except Exception as e:
                logger.error(f"Error embedding {text.get('ref', 'unknown')}: {e}")
        
        logger.info(f"\n✓ Generated {len(embeddings)} embeddings")
        
        # Convert to numpy array
        embeddings_array = np.array(embeddings)
        
        return embeddings_array, metadata
    
    def save_embeddings(self, embeddings: np.ndarray, metadata: List[Dict]):
        """Save embeddings and metadata to disk"""
        logger.info("\n" + "="*80)
        logger.info("SAVING EMBEDDINGS")
        logger.info("="*80)
        
        # Save embeddings as numpy array
        embeddings_path = self.output_dir / "embeddings.npy"
        np.save(embeddings_path, embeddings)
        logger.info(f"✓ Saved embeddings: {embeddings_path}")
        logger.info(f"  Size: {embeddings.nbytes / (1024**2):.1f} MB")
        
        # Save metadata as JSON
        metadata_path = self.output_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ Saved metadata: {metadata_path}")
        
        logger.info("\n" + "="*80)
        logger.info("SETUP COMPLETE!")
        logger.info("="*80)
        logger.info("You can now run the backend with vector search enabled")
        logger.info("The embeddings will be loaded automatically when needed")


def main():
    parser = argparse.ArgumentParser(
        description="Generate BEREL embeddings for Sefaria texts"
    )
    parser.add_argument(
        "--sefaria-path",
        type=str,
        required=True,
        help="Path to Sefaria export directory"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="embeddings",
        help="Output directory for embeddings (default: embeddings/)"
    )
    
    args = parser.parse_args()
    
    # Check if path exists
    sefaria_path = Path(args.sefaria_path)
    if not sefaria_path.exists():
        logger.error(f"Sefaria path does not exist: {sefaria_path}")
        return
    
    # Initialize generator
    generator = SefariaEmbeddingGenerator(output_dir=args.output_dir)
    
    # Load Sefaria texts
    texts = generator.load_sefaria_texts(sefaria_path)
    if not texts:
        logger.error("No texts loaded! Check your Sefaria path and format")
        return
    
    # Generate embeddings
    embeddings, metadata = generator.generate_embeddings(texts)
    
    # Save to disk
    generator.save_embeddings(embeddings, metadata)


if __name__ == "__main__":
    main()
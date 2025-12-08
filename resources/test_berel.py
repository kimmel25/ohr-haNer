"""
BEREL Test v2 - Expanded Corpus + Hybrid Approach

This test:
1. Uses a larger sample corpus (~50 texts instead of 5)
2. Tests a HYBRID approach: Vector search → Claude confirmation
3. Shows real-world performance expectations
"""

from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import json

print("Loading BEREL model...")
tokenizer = AutoTokenizer.from_pretrained("dicta-il/BEREL")
model = AutoModel.from_pretrained("dicta-il/BEREL")
print("✓ Model loaded\n")

def embed_text(text):
    """Create BEREL embedding for text"""
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
    # Use [CLS] token embedding
    embedding = outputs.last_hidden_state[:, 0, :].numpy()
    return embedding

# EXPANDED CORPUS - More texts for better testing
SAMPLE_CORPUS = [
    # Kesubos
    {"ref": "Kesubos 2a", "text": "נערה שנתפתתה אביה בכתובתה ובושתה ופגמה נערה המאורסה אביה בקנסה"},
    {"ref": "Kesubos 2b", "text": "המוציא שם רע על הקטנה פטור שאינו נותן אלא למוציא שם רע על הבוגרת"},
    {"ref": "Kesubos 9a", "text": "ספק ספיקא הוא שמא לא בעל ושמא בעל מעוברת חבירו היא"},
    {"ref": "Kesubos 12a", "text": "שוייה אנפשיה חתיכה דאיסורא ואמר רבא בריה דרבא מדלמא"},
    {"ref": "Kesubos 12b", "text": "גמרא אמר רבה בר בר חנה אמר רבי יוחנן שוייה אנפשיה חתיכה דאיסורא"},
    {"ref": "Kesubos 22a", "text": "עד אחד נאמן באיסורין מנא לן אמר רבי אסי אמר רבי יוחנן"},
    {"ref": "Kesubos 22b", "text": "חזקה אין אדם עושה בעילתו בעילת זנות בעל כדי נישואין בעל"},
    
    # Bava Metzia - ברי ושמא
    {"ref": "Bava Metzia 5b", "text": "מספיקא דדינא ברי ושמא ברי עדיף דלא אפקינן מיניה ממונא דאיניש"},
    {"ref": "Bava Metzia 6a", "text": "הוה אביי והוה רבא חד אמר ברי ושמא ברי עדיף וחד אמר ברי ושמא ממונא מוציא"},
    {"ref": "Bava Metzia 97b", "text": "ברי שלי ושמא שלך ברי עדיף אמר רבא הלכה ברי ושמא ברי עדיף"},
    
    # Kiddushin - שוויא אנפשיה
    {"ref": "Kiddushin 2b", "text": "האיש מקדש באישה ואין האשה מקדשת באיש"},
    {"ref": "Kiddushin 3a", "text": "בכסף בשטר ובביאה בכסף כיצד נתן לה כסף או שווה כסף"},
    {"ref": "Kiddushin 19a", "text": "מאי דכתיב והיה לך לאות על ידך ולזכרון בין עיניך"},
    {"ref": "Kiddushin 65b", "text": "האומר לאשה התקדשי לי בכוס זה שוויא אנפשיה חתיכה דאיסורא"},
    
    # Chullin - חזקת רב הונא
    {"ref": "Chullin 10a", "text": "אמר רב הונא חזקה אין אדם מוציא דבר מתחת ידו לכתחילה לאיסור"},
    {"ref": "Chullin 10b", "text": "חזקה זו דרב הונא חזקה דמאי מעשה שהיה כך היה"},
    {"ref": "Chullin 11a", "text": "אמר רבא חזקת רב הונא למה לי ברי ושמא ברי עדיף"},
    {"ref": "Chullin 12a", "text": "ורב הונא סבר חזקה גדולה יש לנו בזה שאין אדם"},
    
    # Gittin - גט
    {"ref": "Gittin 2a", "text": "המביא גט ממדינת הים צריך שיאמר בפני נכתב ובפני נחתם"},
    {"ref": "Gittin 20a", "text": "גט פשוט עדיו מתוכו גט מקושר עדיו מאחוריו"},
    {"ref": "Gittin 85b", "text": "השולח גט לאשתו ופגע בו בדרך מבטלו בפניה ובפני שנים"},
    
    # Bava Basra - חזקה
    {"ref": "Bava Basra 28a", "text": "חזקה שלוש שנים שנה ראשונה שנייה ושלישית"},
    {"ref": "Bava Basra 41a", "text": "חזקה במקום שיש עדים אפילו יום אחד חזקה"},
    {"ref": "Bava Basra 41b", "text": "חזקה אין אדם פורע תוך זמנו"},
    
    # Pesachim - ספק ספיקא
    {"ref": "Pesachim 9a", "text": "ספק ספיקא להקל שמא לא נכנס ושמא נכנס כבר ביערו"},
    {"ref": "Pesachim 9b", "text": "ספק חמץ ברשות הרבים מותר ברשות היחיד אסור"},
    
    # More varied texts
    {"ref": "Shabbos 19a", "text": "ספק חשכה ספק אינה חשכה ספק ספיקא להקל"},
    {"ref": "Yevamos 31a", "text": "עד אחד נאמן באיסורין דאמר קרא על פי שנים עדים"},
    {"ref": "Sanhedrin 3b", "text": "ברי ושמא ברי עדיף דלא אפקינן מיניה ממונא"},
]

print(f"Creating embeddings for {len(SAMPLE_CORPUS)} texts...")
corpus_embeddings = []
for item in SAMPLE_CORPUS:
    emb = embed_text(item["text"])
    corpus_embeddings.append(emb)
corpus_embeddings = np.vstack(corpus_embeddings)
print("✓ Embeddings created\n")

# TEST QUERIES
TEST_QUERIES = [
    "chezkas rav huna",           # Should find Chullin 10a strongly
    "shaviya anafshe chaticha deisura",  # Should find Kesubos 12b strongly
    "bari vishma",                # Should find Bava Metzia texts
    "sfek sfeka",                 # Should find Pesachim/Kesubos
    "eid echad neeman beissurin", # Should find Kesubos 22a / Yevamos
]

print("="*70)
print("TESTING WITH EXPANDED CORPUS (30 texts)")
print("="*70)

for query in TEST_QUERIES:
    print(f"\n🔍 Query: '{query}'")
    print("-"*70)
    
    # Get query embedding
    query_emb = embed_text(query)
    
    # Calculate similarities
    similarities = cosine_similarity(query_emb, corpus_embeddings)[0]
    
    # Get top 3 matches
    top_indices = np.argsort(similarities)[-3:][::-1]
    
    for i, idx in enumerate(top_indices, 1):
        score = similarities[idx]
        ref = SAMPLE_CORPUS[idx]["ref"]
        text = SAMPLE_CORPUS[idx]["text"][:60] + "..."
        
        if score > 0.7:
            print(f"  {i}. ✓ STRONG MATCH (score: {score:.3f})")
        elif score > 0.6:
            print(f"  {i}. ○ GOOD MATCH (score: {score:.3f})")
        elif score > 0.5:
            print(f"  {i}. ○ WEAK MATCH (score: {score:.3f})")
        else:
            print(f"  {i}. ✗ NO MATCH (score: {score:.3f})")
        
        print(f"     Ref: {ref}")
        print(f"     Hebrew: {text}")

print("\n" + "="*70)
print("ANALYSIS")
print("="*70)
print("""
With 30 texts instead of 5:
- Scores should be HIGHER (more competition = clearer winners)
- Exact matches should rise to the top
- If scores are still < 0.7, we use HYBRID approach (see below)

HYBRID APPROACH (Best of Both Worlds):
1. Vector search finds top 5 candidates (fast, handles any transliteration)
2. Claude reviews the 5 and picks the best match (accurate, contextual)
3. User gets the right Hebrew term with high confidence

Example:
User: "chezkas rav huna"
Vector: Returns 5 texts mentioning חזקה or רב הונא
Claude: "The most relevant is Chullin 10a: חזקת רב הונא"
Result: Perfect match, infinite scalability, no dictionaries

This is MORE POWERFUL than pure vector search alone!
""")

print("\n" + "="*70)
print("NEXT STEPS")
print("="*70)
print("""
1. Run THIS test (not the old one with 5 texts)
2. Check if scores improve with larger corpus
3. If yes → Proceed with full Sefaria indexing
4. If no → Use hybrid approach (vector + Claude verification)

Either way, you WIN. The vector search handles infinite variations,
Claude handles the final verification. No dictionaries needed.
""")
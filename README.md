# Marei Mekomos - מראי מקומות

A tool that finds relevant Torah sources for any topic by combining Claude AI's knowledge with Sefaria's text database.

## How It Works

1. **You enter a topic** (e.g., "kibud av v'em", "bedikas chometz", "tefilla b'tzibur")
2. **Claude AI** suggests relevant source references (pesukim, gemaras, rishonim, etc.)
3. **Sefaria API** fetches the actual Hebrew/English texts
4. **You get organized marei mekomos** with real, verified sources

The key insight: Claude knows *where* to look, but Sefaria provides the *actual texts*. If Claude suggests a source that doesn't exist, Sefaria's API won't find it, so we filter it out. This prevents hallucinations!

---

## Setup Instructions

### Prerequisites
- Python 3.9+ 
- Node.js 18+
- An Anthropic API key (see below)

### Step 1: Get Your Anthropic API Key

1. Go to https://console.anthropic.com/
2. Create an account (or sign in)
3. Go to "API Keys" and create a new key
4. Copy the key - you'll need it in Step 3

**Cost:** Claude Sonnet costs ~$3 per million input tokens. A typical search uses maybe 1,000-2,000 tokens, so each search costs about $0.01-0.02 (one to two cents).

### Step 2: Set Up the Backend (Python)

```bash
# Navigate to backend folder
cd backend

# Create a virtual environment (recommended)
python -m venv venv

# Activate it:
# On Mac/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Set Your API Key

**On Mac/Linux:**
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

**On Windows (Command Prompt):**
```cmd
set ANTHROPIC_API_KEY=your-api-key-here
```

**On Windows (PowerShell):**
```powershell
$env:ANTHROPIC_API_KEY="your-api-key-here"
```

### Step 4: Run the Backend

```bash
# Make sure you're in the backend folder with venv activated
python main.py
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 5: Set Up the Frontend (React)

Open a **new terminal** and:

```bash
# Navigate to frontend folder
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

You should see:
```
VITE v5.x.x ready in xxx ms
➜ Local: http://localhost:5173/
```

### Step 6: Use It!

1. Open http://localhost:5173 in your browser
2. Enter a topic in Hebrew or English
3. Select your level (beginner/intermediate/advanced)
4. Click "Find Sources"

---

## Project Structure

```
marei-mekomos/
├── backend/
│   ├── main.py           # FastAPI server with Claude + Sefaria integration
│   └── requirements.txt  # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx       # Main React component
│   │   ├── App.css       # Styles
│   │   └── main.jsx      # Entry point
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└── README.md
```

---

## API Endpoints

### POST /search

Find sources for a topic.

**Request:**
```json
{
  "topic": "kibud av v'em",
  "level": "intermediate"
}
```

**Response:**
```json
{
  "topic": "kibud av v'em",
  "summary": "The mitzvah to honor one's parents...",
  "sources": [
    {
      "ref": "Shemot 20:12",
      "category": "Chumash",
      "he_text": "כַּבֵּד אֶת אָבִיךָ וְאֶת אִמֶּךָ...",
      "en_text": "Honor your father and your mother...",
      "he_ref": "שמות כ:יב",
      "sefaria_url": "https://www.sefaria.org/Shemot.20.12",
      "found": true
    }
  ]
}
```

---

## Troubleshooting

**"Error connecting to server"**
- Make sure the backend is running on port 8000
- Check that you set the ANTHROPIC_API_KEY

**"No sources found"**
- Try different spelling or wording
- Try Hebrew or English
- The topic might be too obscure

**Sources missing texts**
- Some sources on Sefaria don't have English translations
- The source reference format might not match exactly

---

## Future Ideas

- [ ] Save favorite searches
- [ ] Export as PDF/Word for printing
- [ ] Add more source categories (Midrash, Zohar, etc.)
- [ ] User accounts
- [ ] Payment/subscription system
- [ ] Mobile app

---

## Tech Stack

- **Backend:** Python, FastAPI, Anthropic SDK
- **Frontend:** React, Vite
- **APIs:** Claude AI (Anthropic), Sefaria

---

## License

MIT - Use it however you want!

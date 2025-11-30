# Resources Folder - Living Knowledge

This folder is the "brain" of Marei Mekomos. Claude reads from here dynamically at runtime, so whatever you add becomes part of its knowledge base.

## How It Works

1. **Drop files here** → Claude learns from them on every search
2. **Nothing is hardcoded** → These are starting points, not final answers
3. **Add more over time** → The system gets smarter as you add resources

## Folder Structure

```
resources/
├── knowledge/           # Things Claude should learn FROM
│   ├── masechtos/       # Masechta-specific insights
│   │   ├── kesubos.md   # Your Kesubos learning notes
│   │   ├── pesachim.md  # Your Pesachim notes
│   │   └── ...
│   ├── methodology/     # How to trace sources
│   │   ├── sugya_archaeology.md
│   │   └── citation_patterns.md
│   ├── commentators/    # Who to prioritize for what topics
│   │   ├── acharonim_by_masechta.md
│   │   └── rishonim_overview.md
│   └── examples/        # Good search examples
│       ├── chuppas_niddah.md
│       └── bitul_chametz.md
│
└── feedback/            # Claude learns from past successes/failures
    ├── successful_searches.json
    └── failed_patterns.json
```

## File Formats

Claude can read:
- `.md` (Markdown) - Best for learning notes
- `.json` - Best for structured data
- `.txt` - Plain text

## Example: Adding Your Kesubos Notes

1. Save your סיכום הסוגיא as `knowledge/masechtos/kesubos.md`
2. Next time you search a Kesubos topic, Claude will reference it
3. Claude uses it as a STARTING POINT, not a final answer

## The Philosophy

> "I dont want any of the resources to be final. Its a start/resource for you to build off of."

This folder embodies that. Claude treats everything here as:
- **Starting points** for investigation
- **Examples** of good methodology
- **Hints** about where to look
- **Patterns** to recognize

But never as the FINAL answer. Claude still thinks, validates against Sefaria, and discovers new sources.

## Adding Feedback

After a search, you can add feedback:
```
POST /feedback
{
  "query": "chuppas niddah",
  "good_sources": ["Kesubos 4a", "Rambam Ishus 10:11"],
  "bad_sources": ["Shabbos 130a"],  // irrelevant
  "notes": "The Ran in Nedarim is also important here"
}
```

This gets stored and Claude learns from it for future searches.

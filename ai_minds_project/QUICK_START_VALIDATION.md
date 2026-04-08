# Quick Start: Testing & Validating by Eye

## 🚀 Step-by-Step Testing

### Step 1: Run the Pipeline
```bash
python src/main.py
```
Wait until you see: ✓ Memory processor completed successfully

### Step 2: Run the Interactive Validator
```bash
python validate_outputs.py
```

### Step 3: Follow the Menu
Choose from:
- **Option 1**: See all files, sizes, and chunk counts
- **Option 2**: Read the AI-generated summaries
- **Option 3**: See extracted keywords
- **Option 4**: Check embedding statistics
- **Option 8**: Get accuracy scorecard (★ START HERE)

---

## 👁️ What to Look For (Manual Inspection)

### CSV File (`output/metadata_embeddings.csv`)
**Location**: Right-click > Open With > Excel or VS Code

**What to check**:
```
✓ doc_id          - Sequential numbers (1, 2, 3...)
✓ file_name       - Your actual file names
✓ modality        - Should be "text", "pdf", "image", "audio"
✓ file_size_bytes - Should match your actual file sizes
✓ num_chunks      - Number of text pieces extracted
✓ summary         - 80-200 character AI summary
✓ keywords        - Relevant terms extracted
✓ embedding_dimension - Should always be 384
```

**Good signs** ✓:
- All rows have data (no empty cells)
- Summaries make sense and match file content
- Keywords are relevant to the file
- Chunk counts are reasonable (1-10 per file)

**Bad signs** ✗:
- Empty values in important columns
- num_chunks = 0 (no text extracted)
- summary is gibberish
- keywords are random words

---

### JSON File (`output/metadata_embeddings.json`)
**Location**: Right-click > Open With > VS Code (better for reading)

**Structure to verify**:
```json
{
  "documents": [
    {
      "id": "doc_1",
      "file_metadata": {
        "file_name": "example.txt",
        "modality": "text"
      },
      "chunks": [
        {
          "text": "First 512 characters of file...",
          "embedding": [0.1234, -0.0567, ...384 values total]
        }
      ]
    }
  ]
}
```

**What to check**:
```
✓ Each document has an ID
✓ Each chunk has text (50+ characters)
✓ Each embedding array has exactly 384 numbers
✓ Embedding values are between -1.0 and +1.0
✓ Numbers are mixed (some positive, some negative)
✓ No null or NaN values
```

---

## 🔬 Accuracy Testing (By Eye)

### Test 1: Metadata Accuracy
**What to do**:
1. Open one of your original files (e.g., `data/cognitive_systems.txt`)
2. Check file size in properties
3. Compare with `file_size_bytes` in CSV
4. Should match exactly ✓

**Expected accuracy**: 100%

### Test 2: Summary Accuracy
**What to do**:
1. Read one of your original documents
2. Read the generated summary from CSV
3. Ask yourself: "Does this capture the main idea?"
4. Check for factual errors

**Scoring**:
- 10/10: Captures main topic, accurate, concise
- 8/10: Mostly accurate, minor omissions
- 5/10: Some accuracy, but missing key points
- 2/10: Inaccurate or misleading

**Expected accuracy**: 7-10 / 10

### Test 3: Keywords Accuracy
**What to do**:
1. Read your original document
2. Check if keywords from CSV appear in the text
3. Are they relevant and important?

**Scoring**:
- 10/10: All 5 keywords are relevant and appear in text
- 8/10: 4-5 keywords are relevant
- 5/10: 2-3 keywords match
- 2/10: Keywords unrelated to content

**Expected accuracy**: 8-10 / 10

### Test 4: Embedding Quality
**What to do**:
1. Run: `python validate_outputs.py`
2. Choose Option 4 (Embedding Statistics)
3. Look for:
   - Dimension = 384 ✓
   - Min/Max between -1 and +1 ✓
   - Mixed positive and negative values ✓
   - Std Dev around 0.1-0.3 ✓

**Expected accuracy**: 100%

### Test 5: Semantic Similarity
**What to do**:
1. Run: `python validate_outputs.py`
2. Choose Option 7 (Calculate Similarities)
3. Look at the similarity matrix
4. Similar documents should have high scores (0.7+)
5. Different documents should have lower scores (0.3-0.5)

**Expected accuracy**: Documents on same topic should be 0.7+

---

## 📊 Quick Accuracy Scorecard

Create this table as you test:

```
Metric                    Target      Your Score    Status
─────────────────────────────────────────────────────────
Metadata Completeness     100%        ____%        □ PASS
Summary Relevance         8/10        ___/10       □ PASS
Keywords Relevance        8/10        ___/10       □ PASS
Embedding Dimension       384         ___          □ PASS
Embedding Value Range     [-1, +1]    Check        □ PASS
Mixed Signs               Yes         Yes/No       □ PASS
No NaN/Inf Values         Yes         Yes/No       □ PASS
Semantic Similarity       0.7+        ___          □ PASS

OVERALL SCORE: ____/100
```

---

## 🐛 Troubleshooting

### Issue: "File not found" when running validator
**Solution**: 
1. Make sure you ran `python src/main.py` first
2. Check that output files exist: `output/metadata_embeddings.json`

### Issue: CSV is empty or has only 1 row
**Solution**:
1. Check your `data/` folder has files
2. Run pipeline again: `python src/main.py`

### Issue: Embeddings are all zeros or identical
**Solution**:
1. Restart Python kernel (your environment)
2. Delete `output/` folder and run pipeline again

### Issue: Summaries are too short or empty
**Solution**:
1. Check Ollama is running: `ollama serve`
2. Verify model installed: `ollama list`
3. Try reprocessing: `python src/main.py`

---

## 🎯 Success Criteria

✓ **System is working well if**:
- All files are processed (CSV has rows for your files)
- Summaries make sense and are 80+ characters
- Keywords are relevant (you recognize them in the text)
- Embeddings are 384 dimensions
- No errors in the terminal output

✓ **System is working EXCELLENTLY if**:
- All above + similarity scores match intuition
- Keywords appear in the original text
- Summaries could be publication-quality
- Processing completes in <10 seconds

---

## 📚 Next Steps

After validation:
1. **For Search** → Use embeddings with cosine similarity
2. **For QA** → Send chunks + summaries to Ollama
3. **For Storage** → Save embeddings to Qdrant/Weaviate
4. **For Scale** → Process entire corpus with `process_directory()`

---

## 💡 Tips

- **Test with your own files**: Put them in `data/` folder
- **Spot check**: Validate 1-2 files manually first, then trust the system
- **Compare runs**: Process same file twice, embeddings should be identical
- **Benchmark**: Note processing time for comparing improvements

Happy testing! 🚀

# Testing & Validation Guide - AI MINDS Cognitive Memory System

## 🎯 Overview

You now have **3 powerful tools** to test and validate your system:

1. **`test_accuracy.py`** - Automated testing (10 seconds)
2. **`validate_outputs.py`** - Interactive validation (manual inspection)
3. **`QUICK_START_VALIDATION.md`** - Reference guide (print & check)

---

## ⚡ Quick Start (5 minutes)

### 1. Run the Pipeline
```bash
python src/main.py
```
Wait for: `✓ Memory processor completed successfully`

### 2. Run Automated Tests
```bash
python test_accuracy.py
```
This will show you a **scorecard** with overall system accuracy.

### 3. Review Results
Look for:
- ✓ All metrics showing 85%+ 
- ✓ Overall accuracy 90%+
- ✓ Status = PASS

**Done!** If everything shows PASS, your system is working.

---

## 🔍 Full Validation (20 minutes)

### Step 1: Automated Tests
```bash
python test_accuracy.py
```

**What you'll see**:
```
Metadata Completeness          100.0%
Summary Length Validity         90.0%
Keywords Present                85.0%
Embedding Dimension (384)      100.0%
...
OVERALL SYSTEM ACCURACY         95.2%
```

**Save this score!** It's your baseline.

### Step 2: Interactive Inspection
```bash
python validate_outputs.py
```

**Menu appears - choose**:
- `1` = See all files & metadata
- `2` = Read AI summaries  
- `3` = See extracted keywords
- `4` = Check embedding stats
- `8` = Full accuracy scorecard

### Step 3: Manual Eye Check
Open `output/metadata_embeddings.csv` in Excel and verify:

| Check | Expected | Your Result |
|-------|----------|-------------|
| All files listed? | Yes | ☐ |
| Summaries make sense? | Yes | ☐ |
| Keywords are relevant? | Yes | ☐ |
| No empty cells? | Correct | ☐ |
| Chunk counts > 0? | Correct | ☐ |

### Step 4: Spot Check 1 File
1. Open your original file: `data/example.txt`
2. Open CSV and find the row for `example.txt`
3. Compare:
   - File size in properties vs CSV `file_size_bytes` → **Should match exactly**
   - Summary in CSV → **Should match the main idea of the file**
   - Keywords in CSV → **Should appear somewhere in the text**

---

## 🧪 Detailed Testing (Use These Tools)

### Tool 1: `test_accuracy.py` (Automated)

**When to use**: After every run of `src/main.py`

**What it tests**:
```
✓ Metadata Completeness - All fields filled?
✓ Summary Length - 80-500 characters?
✓ Keywords Present - 4-7 per document?
✓ Embedding Dimension - 384 dimensions?
✓ Embedding Value Range - Between -1 and +1?
✓ Embedding Mixed Signs - Both + and -?
✓ Chunk Text Populated - All chunks have content?
✓ No Missing Values - No NaN/Inf?
✓ Valid Modality - text/pdf/image/audio?
```

**Run it**:
```bash
python test_accuracy.py
```

**Output**: Accuracy scorecard + JSON report saved to `output/accuracy_report.json`

---

### Tool 2: `validate_outputs.py` (Interactive)

**When to use**: For deep inspection and debugging

**What it can do**:
- Display metadata in table format
- Read all summaries
- Show all keywords
- Analyze embedding statistics
- Calculate similarity between documents
- Validate data integrity
- Generate accuracy scorecard

**Run it**:
```bash
python validate_outputs.py
```

**Example session**:
```
🧪 INTERACTIVE TESTING MENU
1. Display CSV Metadata Summary
2. Display Text Summaries
3. Display Keywords
4. Display Embedding Statistics
5. Validate All Metadata
6. Validate Embeddings
7. Calculate Semantic Similarities
8. Full Accuracy Scorecard
9. Exit

Select option (1-9): 8
```

---

### Tool 3: `QUICK_START_VALIDATION.md`

**When to use**: Reference guide for manual inspections

**What it covers**:
- What to check in CSV files
- What to check in JSON files
- Test 1: Metadata Accuracy
- Test 2: Summary Accuracy
- Test 3: Keywords Accuracy
- Test 4: Embedding Quality
- Test 5: Semantic Similarity
- Troubleshooting guide

---

## 📊 Understanding Your Scores

### Accuracy Ranges

```
95-100%  🎉 Excellent  → Production Ready
85-94%   ✓ Good        → Most Use Cases OK
75-84%   ⚠ Acceptable  → Fix Issues
<75%     ✗ Poor        → Debug Needed
```

### What Each Score Means

**Metadata Completeness (95%+)**
- All files have names, sizes, types
- All fields populated
- Timestamps valid

**Summary Quality (80%+)**
- Summaries 80-500 characters
- Match main ideas of documents
- Factually accurate

**Keywords Quality (85%+)**
- 4-7 keywords per document
- Keywords appear in actual text
- Relevant and important

**Embedding Quality (99%+)**
- Always 384 dimensions
- Values between -1 and +1
- Both positive and negative values
- No NaN or Inf values

**Data Quality (100%)**
- All chunks have text
- No corrupt values
- Valid modality types

---

## 🔧 Troubleshooting

### "Low Score - Metadata Completeness"
**Problem**: 70% accuracy on metadata

**Check**:
1. Look at CSV - are there empty cells?
2. Check data folder - are files there?

**Fix**:
```bash
rm -r output/
python src/main.py
python test_accuracy.py
```

---

### "Low Score - Summary Quality"
**Problem**: 50% accuracy on summary length

**Check**:
1. Open CSV - are summaries empty?
2. Is Ollama running?

**Fix**:
```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Run pipeline
python src/main.py
python test_accuracy.py
```

---

### "Low Score - Embeddings"
**Problem**: Embedding dimension is 0

**Check**:
1. Did HuggingFace model download?
2. Enough GPU/CPU memory?

**Fix**:
```bash
# Reinstall transformers
pip install --upgrade sentence-transformers torch

# Clear cache
rm -rf ~/.cache/huggingface

# Run again
python src/main.py
python test_accuracy.py
```

---

## 📈 Improvement Checklist

After your first test run, use this to improve:

- [ ] Score is 90%+
- [ ] All metadata fields populated
- [ ] Summaries are coherent (make sense)
- [ ] Keywords are relevant and appear in text
- [ ] No errors in terminal output
- [ ] Processing time < 10 seconds
- [ ] Embeddings visualize as diverse (not identical)
- [ ] Similarity between related docs is 0.7+
- [ ] No NaN or Inf values in embeddings
- [ ] Can search by keyword and get results

---

## 🚀 Next Steps After Validation

### If Score 90%+:
1. **Add to Vector Database**
   - See: `VECTOR_DB_INTEGRATION.py`
   - Supports: Qdrant, Weaviate, LanceDB

2. **Build Search Interface**
   - Use embeddings for semantic search
   - Use keywords for keyword search
   - Combine both for hybrid search

3. **Connect to RAG Pipeline**
   - Send chunks to Ollama
   - Use summaries as context
   - Build question-answering system

### If Score 70-90%:
1. **Identify low-scoring component**
   - Use `test_accuracy.py` to pinpoint
   - Read the specific test details

2. **Debug that component**
   - Check logs in terminal
   - Read source code
   - Adjust parameters in `src/config.py`

3. **Re-test**
   - Run pipeline again
   - Run accuracy test again

---

## 📝 Sample Test Report

```
🧪 RUNNING AUTOMATED ACCURACY TESTS

✓ Metadata Completeness              100.0%
  └─ 432/432 fields populated

✓ Summary Length Validity             90.0%
  └─ 6/6 summaries in valid range

✓ Keywords Present                    85.0%
  └─ 6/6 documents have keyword sets

✓ Embedding Dimension (384)          100.0%
  └─ 16/16 embeddings have correct dimension

✓ Embedding Value Range              100.0%
  └─ 16/16 embeddings in valid range

✓ Embedding Mixed Signs              100.0%
  └─ 16/16 embeddings have mixed signs

✓ Chunk Text Populated               100.0%
  └─ 16/16 chunks have text

✓ No Missing Values                  100.0%
  └─ 16/16 embeddings have no NaN/Inf

✓ Valid Modality                     100.0%
  └─ 6/6 have valid modality

OVERALL SYSTEM ACCURACY              95.2%

🎉 EXCELLENT! System is working perfectly.
```

---

## 💾 Files You'll Generate

After running tests, these files appear:

```
output/
├── metadata_embeddings.csv      ← Metadata table (open in Excel)
├── metadata_embeddings.json     ← Full data structure (open in VS Code)
├── embeddings_only.json         ← For vector DB import
└── accuracy_report.json         ← Last test results
```

---

## 🎓 Learning from Results

### CSV Shows Low num_chunks
- File might be very short
- Chunking parameters might be too large
- Try lower `CHUNK_SIZE` in config.py

### JSON Shows Identical Embeddings
- Documents might be identical
- Or embeddings not generated properly
- Check they have different text content

### Summaries Are Too Long
- Ollama might be verbose
- Try shorter prompts in embedder.py
- Check `max_tokens` parameter

### Keywords Are Not from Text
- May be "hallucinated" by LLM
- Cross-check against actual document
- This is normal with language models

---

## ✅ Final Checklist

Before declaring "ready for production":

- [ ] Ran `test_accuracy.py` at least once
- [ ] Overall accuracy is 85%+
- [ ] No errors in terminal output
- [ ] Manually verified 2-3 files
- [ ] Summaries are coherent
- [ ] Keywords are relevant
- [ ] Embeddings look reasonable
- [ ] Processing time is acceptable
- [ ] Understood what all tools do
- [ ] Saved accuracy report

**You're ready to deploy!** 🚀

---

## 📞 Quick Command Reference

```bash
# Run pipeline (creates output files)
python src/main.py

# Test accuracy (automated, 10 seconds)
python test_accuracy.py

# Interactive validation menu
python validate_outputs.py

# Check if Ollama is running
curl http://localhost:11434/api/tags

# List available Ollama models
ollama list

# Start Ollama service
ollama serve

# Process a custom folder
python src/main.py --folder data/my_custom_folder

# View last accuracy report
cat output/accuracy_report.json
```

---

Happy testing! 🧪✨

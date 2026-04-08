#!/bin/bash
# Quick Start Script - AI Minds Memory System

echo "============================================================"
echo "🧠 AI MINDS - Cognitive Memory System"
echo "Quick Start & Testing"
echo "============================================================"
echo ""

# Test 1: Check Ollama
echo "1️⃣  Testing Ollama Connection..."
python test_ollama.py
if [ $? -eq 0 ]; then
    echo "✓ Ollama test passed"
else
    echo "✗ Ollama test failed"
    echo "  → Run: ollama serve"
    exit 1
fi

echo ""
echo "2️⃣  Running Integration Tests..."
python test_pipeline.py
if [ $? -ne 0 ]; then
    echo "✗ Integration tests failed"
    exit 1
fi

echo ""
echo "3️⃣  Processing Files..."
python src/main.py
if [ $? -ne 0 ]; then
    echo "✗ File processing failed"
    exit 1
fi

echo ""
echo "============================================================"
echo "✅ ALL TESTS PASSED - SYSTEM READY"
echo "============================================================"
echo ""
echo "Output files in: ./output/"
echo "  • metadata_embeddings.json - Full embeddings + metadata"
echo "  • metadata_embeddings.csv - Searchable summary"
echo "  • embeddings_only.json - Clean embeddings for vector DB"
echo ""
echo "Next steps:"
echo "  1. Copy output files to vector DB"
echo "  2. Implement semantic search"
echo "  3. Build RAG system"
echo ""

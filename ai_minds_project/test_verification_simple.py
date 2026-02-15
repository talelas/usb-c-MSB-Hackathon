"""Direct test of the verification function with sample documents."""
import sys
sys.path.insert(0, '.')

from app.llm.ollama_client import verify_relevance, is_available

print("=" * 70)
print(" Direct Relevance Verification Test ".center(70))
print("=" * 70)

# Check Ollama
print("\nChecking Ollama server...")
if not is_available():
    print("✗ Ollama is NOT running. Start it with: ollama serve")
    sys.exit(1)
print("✓ Ollama is running\n")

# Test cases
test_cases = [
    {
        "query": "What is a neural network?",
        "documents": [
            ("RELEVANT", "A neural network is a computational model inspired by biological neurons. It consists of interconnected layers of nodes that process information through weighted connections."),
            ("RELEVANT", "Neural networks learn by adjusting connection weights through backpropagation. They are fundamental to deep learning and can recognize patterns in data."),
            ("IRRELEVANT", "Climate change refers to long-term shifts in global weather patterns. Rising temperatures affect ecosystems worldwide."),
            ("IRRELEVANT", "The history of ancient Rome includes the expansion of the empire across Europe and the Mediterranean."),
        ]
    },
    {
        "query": "How does machine learning work?",
        "documents": [
            ("RELEVANT", "Machine learning algorithms learn patterns from training data without being explicitly programmed. Common types include supervised, unsupervised, and reinforcement learning."),
            ("MARGINAL", "Artificial intelligence encompasses various technologies including machine learning, natural language processing, and computer vision."),
            ("IRRELEVANT", "Python is a popular programming language used for web development, data analysis, and automation tasks."),
        ]
    },
]

# Run tests
for test_num, test in enumerate(test_cases, 1):
    print("=" * 70)
    print(f" Test Case {test_num} ".center(70))
    print("=" * 70)
    print(f"\nQuery: \"{test['query']}\"\n")
    
    correct = 0
    total = 0
    
    for expected, doc_text in test['documents']:
        total += 1
        # Show document preview
        preview = doc_text[:80] + "..." if len(doc_text) > 80 else doc_text
        print(f"\nDocument {total}:")
        print(f"  Text: {preview}")
        print(f"  Expected: {expected}")
        
        # Verify
        print(f"  Verifying...", end="")
        is_relevant = verify_relevance(test['query'], doc_text)
        result = "RELEVANT" if is_relevant else "IRRELEVANT"
        print(f" {result}")
        
        # Check if correct
        if expected == "MARGINAL":
            # Marginal cases can go either way
            status = "⚠ MARGINAL (either result is acceptable)"
        elif (expected == "RELEVANT" and is_relevant) or (expected == "IRRELEVANT" and not is_relevant):
            status = "✓ CORRECT"
            correct += 1
        else:
            status = "✗ INCORRECT"
        
        print(f"  Status: {status}")
    
    # Show accuracy for this test case
    print(f"\n{'─' * 70}")
    accuracy = (correct / total) * 100
    print(f"Accuracy: {correct}/{total} ({accuracy:.0f}%)")

print("\n" + "=" * 70)
print(" Test Complete ".center(70))
print("=" * 70)
print("\nThe verification system uses the LLM to determine relevance.")
print("It should correctly identify relevant vs irrelevant documents.")
print("\nYou can add your own test cases by editing this script!")

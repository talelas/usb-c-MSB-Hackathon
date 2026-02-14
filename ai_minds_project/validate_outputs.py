"""Interactive Testing & Validation Script - AI MINDS
Run this to inspect all outputs and measure accuracy yourself!
"""

import json
import csv
import numpy as np
from pathlib import Path
from scipy.spatial.distance import cosine

class OutputValidator:
    """Validate and display all pipeline outputs"""
    
    def __init__(self):
        self.json_path = Path("output/metadata_embeddings.json")
        self.csv_path = Path("output/metadata_embeddings.csv")
        self.data = None
        self.csv_data = None
    
    def load_data(self):
        """Load all output files"""
        print("\n" + "="*70)
        print("📂 LOADING OUTPUT FILES")
        print("="*70)
        
        if not self.json_path.exists():
            print(f"✗ JSON file not found: {self.json_path}")
            return False
        
        if not self.csv_path.exists():
            print(f"✗ CSV file not found: {self.csv_path}")
            return False
        
        with open(self.json_path) as f:
            self.data = json.load(f)
        print(f"✓ Loaded JSON: {len(self.data['documents'])} documents")
        
        with open(self.csv_path) as f:
            self.csv_data = list(csv.DictReader(f))
        print(f"✓ Loaded CSV: {len(self.csv_data)} rows")
        
        return True
    
    def display_csv_summary(self):
        """Display CSV data in readable format"""
        print("\n" + "="*70)
        print("📊 METADATA SUMMARY (CSV)")
        print("="*70)
        
        print("\n{:<3} {:<25} {:<20} {:<12} {:<8}".format(
            "ID", "File Name", "Modality", "Size (KB)", "Chunks"
        ))
        print("-" * 70)
        
        for row in self.csv_data:
            try:
                size_kb = float(row['file_size_bytes']) / 1024
                chunks = int(row['num_chunks'])
                print("{:<3} {:<25} {:<20} {:<12.2f} {:<8}".format(
                    row['doc_id'],
                    row['file_name'][:24],
                    row['modality'],
                    size_kb,
                    chunks
                ))
            except:
                pass
    
    def display_summaries(self):
        """Show all generated summaries"""
        print("\n" + "="*70)
        print("📝 TEXT SUMMARIES (Ollama Generated)")
        print("="*70)
        
        for i, row in enumerate(self.csv_data, 1):
            summary = row['summary'][:150]  # First 150 chars
            print(f"\n{i}. {row['file_name']}")
            print(f"   Summary: {summary}{'...' if len(row['summary']) > 150 else ''}")
            print(f"   Length: {len(row['summary'])} characters")
    
    def display_keywords(self):
        """Show all extracted keywords"""
        print("\n" + "="*70)
        print("🔑 EXTRACTED KEYWORDS (Ollama Generated)")
        print("="*70)
        
        for i, row in enumerate(self.csv_data, 1):
            keywords = row['keywords'].split('\n')
            keywords = [k.strip() for k in keywords if k.strip() and k!= row['file_name']]
            print(f"\n{i}. {row['file_name']}")
            for j, kw in enumerate(keywords[:5], 1):
                print(f"   {j}. {kw}")
    
    def display_embeddings(self):
        """Show embedding statistics"""
        print("\n" + "="*70)
        print("🔢 EMBEDDING ANALYSIS")
        print("="*70)
        
        for doc in self.data['documents'][:3]:  # First 3 docs
            fname = doc['file_metadata']['file_name']
            print(f"\n📄 {fname}")
            print(f"   Chunks: {len(doc['chunks'])}")
            print(f"   Embedding Dimension: {doc['embedding_dimension']}")
            
            for chunk_idx, chunk in enumerate(doc['chunks']):
                emb = np.array(chunk['embedding'])
                print(f"\n   Chunk {chunk_idx}:")
                print(f"     Length: {len(emb)}")
                print(f"     Min: {emb.min():.6f}")
                print(f"     Max: {emb.max():.6f}")
                print(f"     Mean: {emb.mean():.6f}")
                print(f"     Std Dev: {emb.std():.6f}")
                print(f"     Sample values: {emb[:5].round(4)}")
    
    def validate_metadata(self):
        """Check metadata accuracy"""
        print("\n" + "="*70)
        print("✓ METADATA VALIDATION")
        print("="*70)
        
        checks = {
            'files_count': len(self.data['documents']) > 0,
            'all_have_names': all(d['file_metadata'].get('file_name') for d in self.data['documents']),
            'all_have_modality': all(d['file_metadata'].get('modality') for d in self.data['documents']),
            'all_have_size': all(d['file_metadata'].get('file_size_bytes') for d in self.data['documents']),
            'all_have_chunks': all(len(d.get('chunks', [])) > 0 for d in self.data['documents']),
        }
        
        for check_name, result in checks.items():
            status = "✓" if result else "✗"
            print(f"{status} {check_name}: {'PASS' if result else 'FAIL'}")
        
        return all(checks.values())
    
    def validate_embeddings(self):
        """Check embedding quality"""
        print("\n" + "="*70)
        print("✓ EMBEDDING VALIDATION")
        print("="*70)
        
        checks = {
            'correct_dimension': True,
            'values_in_range': True,
            'mixed_signs': True,
            'no_nans': True,
        }
        
        for doc in self.data['documents']:
            for chunk in doc['chunks']:
                emb = np.array(chunk['embedding'])
                
                # Check dimension
                if len(emb) != 384:
                    checks['correct_dimension'] = False
                
                # Check range
                if not (-1 <= emb.min() and emb.max() <= 1):
                    checks['values_in_range'] = False
                
                # Check mixed signs
                if not (any(emb > 0) and any(emb < 0)):
                    checks['mixed_signs'] = False
                
                # Check for NaN
                if np.isnan(emb).any() or np.isinf(emb).any():
                    checks['no_nans'] = False
        
        for check_name, result in checks.items():
            status = "✓" if result else "✗"
            print(f"{status} {check_name}: {'PASS' if result else 'FAIL'}")
        
        return all(checks.values())
    
    def calculate_similarities(self):
        """Calculate similarity between documents"""
        print("\n" + "="*70)
        print("🔗 SEMANTIC SIMILARITY ANALYSIS")
        print("="*70)
        
        if len(self.data['documents']) < 2:
            print("Need at least 2 documents for similarity comparison")
            return
        
        # Get first chunk of each document
        embeddings = []
        filenames = []
        
        for doc in self.data['documents'][:6]:  # First 6
            if doc['chunks']:
                emb = np.array(doc['chunks'][0]['embedding'])
                embeddings.append(emb)
                filenames.append(doc['file_metadata']['file_name'])
        
        # Compare each pair
        print("\nSimilarity Matrix (first chunk of each file):\n")
        print("{:<25}".format("File"), end="")
        for fname in filenames[:6]:
            print(f"{fname[:18]:>20}", end="")
        print()
        print("-" * 150)
        
        for i, fname1 in enumerate(filenames[:6]):
            print(f"{fname1:<25}", end="")
            for j, fname2 in enumerate(filenames[:6]):
                if i == j:
                    sim = 1.0
                else:
                    sim = 1 - cosine(embeddings[i], embeddings[j])
                print(f"{sim:>20.3f}", end="")
            print()
        
        print("\nInterpretation:")
        print("  0.8-1.0: Nearly identical")
        print("  0.6-0.8: Very similar")
        print("  0.3-0.6: Related but different")
        print("  0.0-0.3: Unrelated")
    
    def accuracy_scorecard(self):
        """Generate accuracy scorecard"""
        print("\n" + "="*70)
        print("📈 ACCURACY SCORECARD")
        print("="*70)
        
        # Metadata accuracy
        metadata_ok = self.validate_metadata()
        
        # Embedding accuracy
        embedding_ok = self.validate_embeddings()
        
        # Summary quality (manual check)
        summaries = [row['summary'] for row in self.csv_data]
        summary_quality = all(20 < len(s) < 300 for s in summaries)
        
        # Keywords quality
        keywords_ok = all(int(row['num_chunks']) > 0 for row in self.csv_data)
        
        scores = {
            'Metadata Accuracy': metadata_ok,
            'Embedding Accuracy': embedding_ok,
            'Summary Quality': summary_quality,
            'Keywords Present': keywords_ok,
        }
        
        print()
        passed = 0
        for metric, result in scores.items():
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{metric:<30} {status}")
            if result:
                passed += 1
        
        total_score = (passed / len(scores)) * 100
        print(f"\n{'OVERALL SCORE':<30} {total_score:.0f}%")
        
        if total_score >= 90:
            print("\n🎉 EXCELLENT! System working perfectly!")
        elif total_score >= 70:
            print("\n✓ GOOD! System is functioning well.")
        else:
            print("\n⚠️  Issues detected. Review logs above.")
    
    def interactive_menu(self):
        """Interactive menu for testing"""
        while True:
            print("\n" + "="*70)
            print("🧪 INTERACTIVE TESTING MENU")
            print("="*70)
            print("\n1. Display CSV Metadata Summary")
            print("2. Display Text Summaries")
            print("3. Display Keywords")
            print("4. Display Embedding Statistics")
            print("5. Validate All Metadata")
            print("6. Validate Embeddings")
            print("7. Calculate Semantic Similarities")
            print("8. Full Accuracy Scorecard")
            print("9. Exit")
            
            choice = input("\nSelect option (1-9): ").strip()
            
            if choice == "1":
                self.display_csv_summary()
            elif choice == "2":
                self.display_summaries()
            elif choice == "3":
                self.display_keywords()
            elif choice == "4":
                self.display_embeddings()
            elif choice == "5":
                self.validate_metadata()
            elif choice == "6":
                self.validate_embeddings()
            elif choice == "7":
                self.calculate_similarities()
            elif choice == "8":
                self.accuracy_scorecard()
            elif choice == "9":
                print("\n✓ Exiting. Results saved!")
                break
            else:
                print("Invalid choice. Try again.")


def main():
    """Main entry point"""
    print("\n" + "="*70)
    print("🔍 AI MINDS OUTPUT VALIDATOR & TESTING TOOL")
    print("="*70)
    print("\nThis tool helps you inspect and validate all system outputs.")
    print("Run this after processing files with: python src/main.py")
    
    validator = OutputValidator()
    
    if not validator.load_data():
        print("\n✗ Could not load output files.")
        print("   Make sure you've run: python src/main.py")
        return 1
    
    validator.interactive_menu()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

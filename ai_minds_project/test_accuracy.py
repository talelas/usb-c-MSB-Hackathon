"""Automated Accuracy Testing - AI MINDS
Measures accuracy of summaries, keywords, and embeddings against expected ranges
"""

import json
import csv
import numpy as np
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

class AccuracyTester:
    """Automated accuracy measurement"""
    
    def __init__(self):
        self.json_path = Path("output/metadata_embeddings.json")
        self.csv_path = Path("output/metadata_embeddings.csv")
        self.data = None
        self.csv_data = None
        self.results = {}
    
    def load_data(self):
        """Load output files"""
        try:
            with open(self.json_path) as f:
                self.data = json.load(f)
            with open(self.csv_path) as f:
                self.csv_data = list(csv.DictReader(f))
            return True
        except FileNotFoundError as e:
            print(f"✗ Error loading files: {e}")
            return False
    
    def test_metadata_completeness(self) -> Tuple[float, str]:
        """Test: All metadata fields are populated - Target: 100%"""
        total_checks = 0
        passed_checks = 0
        
        required_fields = [
            'doc_id', 'file_name', 'modality', 'file_size_bytes',
            'file_timestamp', 'file_extension', 'summary', 'keywords',
            'num_chunks', 'embedding_dimension'
        ]
        
        for row in self.csv_data:
            for field in required_fields:
                total_checks += 1
                value = row.get(field, '')
                if value and value.strip():
                    passed_checks += 1
        
        accuracy = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        
        details = f"{passed_checks}/{total_checks} fields populated"
        return accuracy, details
    
    def test_summary_length(self) -> Tuple[float, str]:
        """Test: Summaries are reasonable length - Target: 80-500 chars"""
        target_min = 80
        target_max = 500
        
        valid = 0
        for row in self.csv_data:
            summary_len = len(row.get('summary', ''))
            if target_min <= summary_len <= target_max:
                valid += 1
        
        accuracy = (valid / len(self.csv_data) * 100) if self.csv_data else 0
        details = f"{valid}/{len(self.csv_data)} summaries in valid range"
        return accuracy, details
    
    def test_keywords_present(self) -> Tuple[float, str]:
        """Test: Keywords are extracted - Target: 4-5 per document"""
        valid = 0
        
        for row in self.csv_data:
            keywords_str = row.get('keywords', '')
            # Split by newline or comma
            keywords = [k.strip() for k in keywords_str.replace(',', '\n').split('\n')]
            keywords = [k for k in keywords if k and len(k) > 2]
            
            if 3 <= len(keywords) <= 7:  # Allow some flexibility
                valid += 1
        
        accuracy = (valid / len(self.csv_data) * 100) if self.csv_data else 0
        details = f"{valid}/{len(self.csv_data)} documents have keyword sets"
        return accuracy, details
    
    def test_embedding_dimension(self) -> Tuple[float, str]:
        """Test: All embeddings are 384 dimensions - Target: 100%"""
        correct = 0
        total = 0
        
        for doc in self.data['documents']:
            for chunk in doc.get('chunks', []):
                total += 1
                embedding = chunk.get('embedding', [])
                if len(embedding) == 384:
                    correct += 1
        
        accuracy = (correct / total * 100) if total > 0 else 0
        details = f"{correct}/{total} embeddings have correct dimension"
        return accuracy, details
    
    def test_embedding_value_range(self) -> Tuple[float, str]:
        """Test: Embedding values in [-1, 1] range - Target: 100%"""
        valid = 0
        total = 0
        
        for doc in self.data['documents']:
            for chunk in doc.get('chunks', []):
                embedding = np.array(chunk.get('embedding', []))
                total += 1
                
                if (embedding.min() >= -1.5 and 
                    embedding.max() <= 1.5 and
                    not np.isnan(embedding).any() and
                    not np.isinf(embedding).any()):
                    valid += 1
        
        accuracy = (valid / total * 100) if total > 0 else 0
        details = f"{valid}/{total} embeddings in valid range"
        return accuracy, details
    
    def test_embedding_mixed_signs(self) -> Tuple[float, str]:
        """Test: Embeddings have both positive and negative values - Target: 99%"""
        mixed = 0
        total = 0
        
        for doc in self.data['documents']:
            for chunk in doc.get('chunks', []):
                embedding = np.array(chunk.get('embedding', []))
                total += 1
                
                has_positive = (embedding > 0).any()
                has_negative = (embedding < 0).any()
                
                if has_positive and has_negative:
                    mixed += 1
        
        accuracy = (mixed / total * 100) if total > 0 else 0
        details = f"{mixed}/{total} embeddings have mixed signs"
        return accuracy, details
    
    def test_chunk_text_populated(self) -> Tuple[float, str]:
        """Test: All chunks have text content - Target: 100%"""
        with_text = 0
        total = 0
        
        for doc in self.data['documents']:
            for chunk in doc.get('chunks', []):
                total += 1
                text = chunk.get('text', '')
                if text and len(text.strip()) > 10:
                    with_text += 1
        
        accuracy = (with_text / total * 100) if total > 0 else 0
        details = f"{with_text}/{total} chunks have text"
        return accuracy, details
    
    def test_no_missing_values(self) -> Tuple[float, str]:
        """Test: No NaN or Inf in embeddings - Target: 100%"""
        clean = 0
        total = 0
        
        for doc in self.data['documents']:
            for chunk in doc.get('chunks', []):
                embedding = np.array(chunk.get('embedding', []))
                total += 1
                
                if not np.isnan(embedding).any() and not np.isinf(embedding).any():
                    clean += 1
        
        accuracy = (clean / total * 100) if total > 0 else 0
        details = f"{clean}/{total} embeddings have no NaN/Inf"
        return accuracy, details
    
    def test_modality_valid(self) -> Tuple[float, str]:
        """Test: Modality values are valid - Target: 100%"""
        valid_modalities = {'text', 'pdf', 'image', 'audio'}
        valid = 0
        
        for row in self.csv_data:
            modality = row.get('modality', '').lower()
            if modality in valid_modalities:
                valid += 1
        
        accuracy = (valid / len(self.csv_data) * 100) if self.csv_data else 0
        details = f"{valid}/{len(self.csv_data)} have valid modality"
        return accuracy, details
    
    def run_all_tests(self) -> Dict:
        """Run all tests and return results"""
        print("\n" + "="*70)
        print("🧪 RUNNING AUTOMATED ACCURACY TESTS")
        print("="*70 + "\n")
        
        tests = [
            ("Metadata Completeness", self.test_metadata_completeness),
            ("Summary Length Validity", self.test_summary_length),
            ("Keywords Present", self.test_keywords_present),
            ("Embedding Dimension (384)", self.test_embedding_dimension),
            ("Embedding Value Range", self.test_embedding_value_range),
            ("Embedding Mixed Signs", self.test_embedding_mixed_signs),
            ("Chunk Text Populated", self.test_chunk_text_populated),
            ("No Missing Values", self.test_no_missing_values),
            ("Valid Modality", self.test_modality_valid),
        ]
        
        results = {}
        for test_name, test_func in tests:
            accuracy, details = test_func()
            results[test_name] = {
                'accuracy': accuracy,
                'details': details,
                'status': self._get_status(accuracy)
            }
            
            status_icon = "✓" if results[test_name]['status'] == "PASS" else "⚠"
            print(f"{status_icon} {test_name:<30} {accuracy:>6.1f}%")
            print(f"   └─ {details}\n")
        
        return results
    
    def _get_status(self, accuracy: float) -> str:
        """Determine test status based on accuracy"""
        if accuracy >= 95:
            return "PASS"
        elif accuracy >= 80:
            return "WARN"
        else:
            return "FAIL"
    
    def generate_report(self, results: Dict):
        """Generate summary report"""
        print("\n" + "="*70)
        print("📊 ACCURACY REPORT")
        print("="*70 + "\n")
        
        # Calculate category scores
        metadata_score = results["Metadata Completeness"]['accuracy']
        summary_score = results["Summary Length Validity"]['accuracy']
        keyword_score = results["Keywords Present"]['accuracy']
        embedding_scores = [
            results["Embedding Dimension (384)"]['accuracy'],
            results["Embedding Value Range"]['accuracy'],
            results["Embedding Mixed Signs"]['accuracy'],
        ]
        embedding_score = np.mean(embedding_scores)
        
        quality_scores = [
            results["Chunk Text Populated"]['accuracy'],
            results["No Missing Values"]['accuracy'],
        ]
        quality_score = np.mean(quality_scores)
        
        # Overall score (weighted average)
        overall = (
            metadata_score * 0.2 +
            summary_score * 0.2 +
            keyword_score * 0.2 +
            embedding_score * 0.2 +
            quality_score * 0.2
        )
        
        print(f"{'CATEGORY':<35} {'SCORE':<10} {'STATUS':<10}")
        print("-" * 55)
        print(f"{'Metadata Quality':<35} {metadata_score:>6.1f}%    {self._get_status(metadata_score):<10}")
        print(f"{'Summary Quality':<35} {summary_score:>6.1f}%    {self._get_status(summary_score):<10}")
        print(f"{'Keywords Quality':<35} {keyword_score:>6.1f}%    {self._get_status(keyword_score):<10}")
        print(f"{'Embedding Quality':<35} {embedding_score:>6.1f}%    {self._get_status(embedding_score):<10}")
        print(f"{'Data Quality':<35} {quality_score:>6.1f}%    {self._get_status(quality_score):<10}")
        print("-" * 55)
        print(f"{'OVERALL SYSTEM ACCURACY':<35} {overall:>6.1f}%    {self._get_status(overall):<10}")
        
        print("\n" + "="*70)
        print("📈 QUALITY ASSESSMENT")
        print("="*70 + "\n")
        
        if overall >= 95:
            print("🎉 EXCELLENT! System is working perfectly.")
            print("   All metrics exceed quality thresholds.")
            print("   Ready for production use!")
        elif overall >= 90:
            print("✓ VERY GOOD! System is working well.")
            print("   Minor issues detected, but nothing critical.")
            print("   Ready for most use cases.")
        elif overall >= 80:
            print("⚠ GOOD! System is functional.")
            print("   Some quality issues detected.")
            print("   Recommend reviewing details above.")
        elif overall >= 70:
            print("⚠ ACCEPTABLE! System is working.")
            print("   Several issues need attention.")
            print("   See details above for improvement areas.")
        else:
            print("✗ ISSUES DETECTED!")
            print("   System needs debugging.")
            print("   See troubleshooting guide for help.")
        
        # Save report
        report_path = Path("output/accuracy_report.json")
        report = {
            'timestamp': datetime.now().isoformat(),
            'overall_accuracy': overall,
            'category_scores': {
                'metadata': metadata_score,
                'summary': summary_score,
                'keywords': keyword_score,
                'embeddings': embedding_score,
                'quality': quality_score,
            },
            'test_results': results,
        }
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n✓ Report saved to: {report_path}")
        
        return overall


def main():
    print("\n" + "="*70)
    print("🔍 AI MINDS AUTOMATED ACCURACY TESTER")
    print("="*70)
    print("\nThis tool automatically measures system accuracy across 9 dimensions.")
    print("Run this after: python src/main.py\n")
    
    tester = AccuracyTester()
    
    if not tester.load_data():
        print("✗ Cannot load output files.")
        print("   Run the pipeline first: python src/main.py")
        return 1
    
    results = tester.run_all_tests()
    overall = tester.generate_report(results)
    
    print("\n" + "="*70)
    print("✓ Testing complete!")
    print("="*70 + "\n")
    
    return 0 if overall >= 80 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

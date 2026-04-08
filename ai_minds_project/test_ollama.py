"""Test Ollama connection and llama 3.2 model"""
import requests
import json
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

# Configuration
OLLAMA_URL = "http://localhost:11434"
MODEL_NAME = "llama3.2"


def check_ollama_status():
    """Check if Ollama service is running"""
    print("\n" + "="*60)
    print("🔍 Checking Ollama Service Status")
    print("="*60)
    
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            print("✓ Ollama service is RUNNING")
            return True
        else:
            print(f"✗ Ollama returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to Ollama at {OLLAMA_URL}")
        print("  → Start Ollama with: ollama serve")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def list_available_models():
    """List all available models in Ollama"""
    print("\n" + "="*60)
    print("📋 Available Models")
    print("="*60)
    
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            
            if not models:
                print("✗ No models installed")
                return []
            
            print(f"Found {len(models)} model(s):\n")
            for model in models:
                name = model.get('name', 'unknown')
                size = model.get('size', 0)
                size_gb = size / (1024**3)
                print(f"  • {name}")
                print(f"    Size: {size_gb:.2f} GB")
                print()
            
            return [m.get('name') for m in models]
        else:
            print(f"✗ Failed to list models: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error: {e}")
        return []


def check_model_installed(model_name):
    """Check if specific model is installed"""
    print("\n" + "="*60)
    print(f"🔎 Checking for Model: {model_name}")
    print("="*60)
    
    try:
        models = list_available_models()
        
        for model in models:
            if model_name.lower() in model.lower():
                print(f"✓ Model '{model_name}' is INSTALLED")
                return True
        
        print(f"✗ Model '{model_name}' NOT found")
        print(f"  → Install with: ollama pull {model_name}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_model_generation(model_name, test_prompt):
    """Test generating text with the model"""
    print("\n" + "="*60)
    print(f"🤖 Testing Model Generation: {model_name}")
    print("="*60)
    
    try:
        print(f"Prompt: '{test_prompt}'")
        print("\nGenerating response...\n")
        
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model_name,
                "prompt": test_prompt,
                "stream": False,
                "temperature": 0.7,
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result.get('response', '')
            
            print("✓ Model responded successfully!")
            print("-" * 60)
            print(generated_text)
            print("-" * 60)
            
            # Performance metrics
            total_duration = result.get('total_duration', 0) / 1e9  # Convert to seconds
            load_duration = result.get('load_duration', 0) / 1e9
            prompt_eval_count = result.get('prompt_eval_count', 0)
            eval_count = result.get('eval_count', 0)
            
            print(f"\n📊 Performance Metrics:")
            print(f"  • Total duration: {total_duration:.2f}s")
            print(f"  • Load duration: {load_duration:.2f}s")
            print(f"  • Prompt tokens: {prompt_eval_count}")
            print(f"  • Generated tokens: {eval_count}")
            if eval_count > 0:
                tokens_per_sec = eval_count / (total_duration - load_duration) if (total_duration - load_duration) > 0 else 0
                print(f"  • Generation speed: {tokens_per_sec:.1f} tokens/sec")
            
            return True
        else:
            print(f"✗ Model generation failed: {response.status_code}")
            print(response.text)
            return False
    except requests.exceptions.Timeout:
        print("✗ Request timed out (model may still be generating)")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_embedding_with_ollama(model_name, text):
    """Test embedding a text (if supported)"""
    print("\n" + "="*60)
    print(f"📝 Testing Embeddings with: {model_name}")
    print("="*60)
    
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={
                "model": model_name,
                "prompt": text,
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            embedding = result.get('embedding', [])
            
            print(f"✓ Embedding generated!")
            print(f"  • Embedding dimension: {len(embedding)}")
            print(f"  • Sample values (first 5): {embedding[:5]}")
            return True
        else:
            print(f"⚠ Embeddings not supported or failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"⚠ Embedding test failed: {e}")
        return False


def main():
    """Run all Ollama tests"""
    print("\n" + "="*60)
    print("🧠 AI MINDS - Ollama Integration Test Suite")
    print("="*60)
    
    # Test 1: Check service
    if not check_ollama_status():
        print("\n❌ OLLAMA SERVICE NOT RUNNING")
        print("Please start Ollama:")
        print("  $> ollama serve")
        return 1
    
    # Test 2: List models
    available_models = list_available_models()
    
    if not available_models:
        print("\n⚠️  NO MODELS INSTALLED")
        print(f"Install llama3.2 with:")
        print(f"  $> ollama pull {MODEL_NAME}")
        return 1
    
    # Test 3: Check specific model
    if not check_model_installed(MODEL_NAME):
        print(f"\n⚠️  {MODEL_NAME} NOT FOUND")
        print(f"Install with: ollama pull {MODEL_NAME}")
        return 1
    
    # Test 4: Generate text
    test_prompt = "What is artificial intelligence in one sentence?"
    if not test_model_generation(MODEL_NAME, test_prompt):
        print("\n❌ MODEL GENERATION FAILED")
        return 1
    
    # Test 5: Test embeddings
    test_embedding_with_ollama(MODEL_NAME, "Artificial intelligence and machine learning")
    
    # Success summary
    print("\n" + "="*60)
    print("✅ OLLAMA INTEGRATION SUCCESSFUL")
    print("="*60)
    print(f"✓ Ollama service: RUNNING")
    print(f"✓ Model '{MODEL_NAME}': INSTALLED & WORKING")
    print(f"✓ Text generation: FUNCTIONAL")
    print("\n🚀 System is ready for memory processing!")
    print("="*60 + "\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

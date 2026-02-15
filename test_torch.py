try:
    import torch
    print(f"Torch: {torch.__version__}")
    print(f"CUDA: {torch.cuda.is_available()}")
except Exception as e:
    print(f"Error: {e}")
except ImportError as e:
    print(f"ImportError: {e}")

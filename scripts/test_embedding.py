#!/usr/bin/env python3
import sys
import time

def main():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("Error: 'sentence-transformers' package not installed.")
        sys.exit(1)

    model_name = "BAAI/bge-base-en-v1.5"
    print(f"Loading embedding model '{model_name}' on CPU...")
    start_time = time.time()
    
    model = SentenceTransformer(model_name, device="cpu")
    load_time = time.time() - start_time
    print(f"Model loaded in {load_time:.2f} seconds.")

    test_sentence = "This is a test sentence for vector embedding."
    print(f"Embedding test sentence: '{test_sentence}'")
    
    embed_start = time.time()
    embedding = model.encode(test_sentence, convert_to_numpy=True)
    embed_time = time.time() - embed_start

    print(f"Embedding shape: {embedding.shape}")
    print(f"Embedding dimension: {len(embedding)}")
    print(f"Embedding compute time: {embed_time:.3f} seconds")
    print(f"Sample values (first 5): {embedding[:5].tolist()}")

    # Clean up reference so memory is freed on exit
    del model
    print("SUCCESS: Embedding model loaded, computed 768-dim embedding, and unloaded successfully.")
    sys.exit(0)

if __name__ == "__main__":
    main()

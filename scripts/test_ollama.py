#!/usr/bin/env python3
import sys

def main():
    try:
        import ollama
    except ImportError:
        print("Error: 'ollama' package not installed in the python environment.")
        sys.exit(1)

    model_name = "qwen3:8b"
    prompt = "Say OK"

    print(f"Connecting to Ollama and querying model '{model_name}'...")
    try:
        client = ollama.Client(host="http://127.0.0.1:11434")
        response = client.generate(model=model_name, prompt=prompt)
        response_text = response.get('response', '')
        print("\n--- Raw Ollama Response ---")
        print(response_text)
        print("---------------------------")
        print("SUCCESS: Ollama + Qwen3:8B is reachable and working!")
        sys.exit(0)
    except ollama.ResponseError as e:
        if "not found" in str(e).lower():
            print(f"Error: Model '{model_name}' not found — run `ollama pull {model_name}`")
        else:
            print(f"Ollama API Error: {e}")
        sys.exit(1)
    except Exception as e:
        print("Ollama not reachable — is it running? Run `ollama serve`")
        print(f"Details: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

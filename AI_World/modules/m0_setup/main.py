import os
import sys
import time
import json
import argparse
import requests

OLLAMA_BASE_URL = "http://localhost:11434"
CONFIG_OUTPUT_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "config.json"
    )
)

BENCHMARK_PROMPTS = [
    "Please describe the world you live in in one sentence in English.",
    "It is spring now, how do you feel? Please answer in one sentence in English.",
    "What is your name and what do you want to do the most? Please answer briefly in English.",
]


def list_models() -> list[str]:
    """
    Call GET /api/tags and return a list of installed local model names.
    Exit with a friendly message if the connection fails.
    """
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        response.raise_for_status()
        data = response.json()
        models = [item["name"] for item in data.get("models", [])]
        return models
    except requests.exceptions.RequestException:
        print("\n[Error] Unable to connect to Ollama service.")
        print("Please verify that Ollama is installed and running (e.g., run `ollama serve` in the terminal).")
        print("You can download it from https://ollama.com.\n")
        sys.exit(1)


def select_model(models: list[str], default_model: str = "gemma4:e4b") -> str:
    """
    Print the model list for the user to choose from.
    If the input is empty and the default model is in the list, use the default.
    """
    if not models:
        print("\n[Warning] No models detected in your Ollama.")
        print(f"Please run `ollama pull {default_model}` in the terminal to download the model first.\n")
        sys.exit(1)

    print("\nLocal Ollama models detected:")
    default_idx = -1
    for idx, model in enumerate(models, 1):
        if model == default_model:
            default_idx = idx
            print(f"  {idx}. {model} (default)")
        else:
            print(f"  {idx}. {model}")

    if default_idx == -1:
        default_idx = 1
        default_model = models[0]
        print(f"\n*(Tip: Press Enter to default to {default_model})")

    while True:
        try:
            choice = input(f"\nPlease select a model number [default {default_idx}]: ").strip()
            if not choice:
                return default_model
            
            val = int(choice)
            if 1 <= val <= len(models):
                return models[val - 1]
            else:
                print(f"[Error] Please enter a valid number between 1 and {len(models)}.")
        except ValueError:
            print("[Error] Invalid input format, please enter an integer.")


def benchmark_model(model_name: str) -> dict:
    """
    Send 3 test prompts to the selected model, timing the responses and calculating tokens/sec.
    """
    print(f"\nBenchmarking model [{model_name}]...")
    results = []

    for idx, prompt in enumerate(BENCHMARK_PROMPTS, 1):
        print(f"  [{idx}/3] Sending Prompt: \"{prompt}\" ... ", end="", flush=True)
        
        start_time = time.time()
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            response = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=60)
            response.raise_for_status()
            elapsed = time.time() - start_time
            data = response.json()
            
            eval_count = data.get("eval_count", 0)
            eval_duration_ns = data.get("eval_duration", 0)
            response_text = data.get("response", "").strip()
            
            if eval_duration_ns > 0:
                tps = eval_count / (eval_duration_ns / 1e9)
            else:
                tps = eval_count / elapsed if elapsed > 0 else 0.0

            results.append({
                "prompt": prompt,
                "response_time_sec": elapsed,
                "eval_count": eval_count,
                "eval_duration_ns": eval_duration_ns,
                "tokens_per_sec": tps,
                "response_preview": response_text[:50] + ("..." if len(response_text) > 50 else "")
            })
            print(f"Done! (Time: {elapsed:.2f}s, Speed: {tps:.2f} tokens/s)")
            
        except requests.exceptions.RequestException as e:
            print(f"Failed!")
            print(f"[Error] API call failed: {e}")
            sys.exit(1)

    avg_response_time = sum(r["response_time_sec"] for r in results) / len(results)
    avg_tps = sum(r["tokens_per_sec"] for r in results) / len(results)
    
    return {
        "avg_response_time_sec": avg_response_time,
        "tokens_per_sec": avg_tps,
        "raw_results": results
    }


def recommend_max_agents(avg_response_time_sec: float) -> int:
    """
    Recommend the maximum number of agents based on average response time.
    """
    if avg_response_time_sec < 2.0:
        return 10
    elif avg_response_time_sec < 5.0:
        return 6
    elif avg_response_time_sec < 10.0:
        return 3
    else:
        return 1


def confirm_max_agents(recommended: int) -> int:
    """
    Let the user confirm or override the recommended number of agents.
    """
    print(f"\nBased on benchmarking, the recommended max agents (MAX_AGENTS) is: {recommended}")
    while True:
        try:
            choice = input(f"Press Enter to confirm, or enter a custom positive integer: ").strip()
            if not choice:
                return recommended
            
            val = int(choice)
            if val > 0:
                return val
            else:
                print("[Error] Number of agents must be greater than 0.")
        except ValueError:
            print("[Error] Please enter a valid positive integer.")


def save_config(
    model_name: str,
    avg_response_time_sec: float,
    tokens_per_sec: float,
    max_agents: int,
) -> None:
    """
    Create and save a config.json matching the Config schema.
    """
    config_data = {
        "ollama_model": model_name,
        "ollama_base_url": OLLAMA_BASE_URL,
        "avg_response_time_sec": round(avg_response_time_sec, 2),
        "tokens_per_sec": round(tokens_per_sec, 2),
        "recommended_max_agents": max_agents,
        "tick_interval_sec": 30,
        "concurrency_mode": "sequential",
        "max_concurrent_requests": 1,
    }
    
    os.makedirs(os.path.dirname(CONFIG_OUTPUT_PATH), exist_ok=True)
    
    with open(CONFIG_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)
        
    print(f"\n[Success] Configuration file successfully created and saved to:")
    print(f" -> {CONFIG_OUTPUT_PATH}\n")


def main():
    parser = argparse.ArgumentParser(description="AI World - M0 Setup & Benchmark Script")
    parser.add_argument("--model", type=str, default="gemma4:e4b", help="Default model name to use")
    parser.add_argument("--non-interactive", action="store_true", help="Enable non-interactive mode")
    parser.add_argument("--agents", type=int, default=None, help="Custom max agents in non-interactive mode")
    args = parser.parse_args()

    print("=" * 50)
    print("  AI World — M0 Environment Setup & Benchmark")
    print("=" * 50)

    models = list_models()

    selected = ""
    if args.non_interactive:
        if args.model in models:
            selected = args.model
        elif len(models) > 0:
            print(f"[Tip] Specified model '{args.model}' not found. Automatically using '{models[0]}'")
            selected = models[0]
        else:
            print(f"[Error] No models found in Ollama. Please run `ollama pull {args.model}` first.")
            sys.exit(1)
    else:
        selected = select_model(models, default_model=args.model)

    bench_results = benchmark_model(selected)

    recommended = recommend_max_agents(bench_results["avg_response_time_sec"])
    final_agents = recommended
    
    if args.non_interactive:
        if args.agents is not None:
            final_agents = args.agents
            print(f"\nNon-interactive mode: Setting MAX_AGENTS = {final_agents}")
        else:
            print(f"\nNon-interactive mode: Using recommended MAX_AGENTS = {final_agents}")
    else:
        final_agents = confirm_max_agents(recommended)

    save_config(
        model_name=selected,
        avg_response_time_sec=bench_results["avg_response_time_sec"],
        tokens_per_sec=bench_results["tokens_per_sec"],
        max_agents=final_agents
    )

    print("=" * 50)
    print("  Benchmark Summary")
    print("=" * 50)
    print(f"  Model Name       : {selected}")
    print(f"  Avg Response Time: {bench_results['avg_response_time_sec']:.2f} s")
    print(f"  Inference Speed  : {bench_results['tokens_per_sec']:.2f} tokens/sec")
    print(f"  Max Agents       : {final_agents}")
    print("=" * 50)


if __name__ == "__main__":
    main()

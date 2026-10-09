#!/usr/bin/env python
"""
Benchmark script to test LLM candidates for NIM Sentinel.
Tests candidate models with 3 calls each + structured output (JSON) test.

Measures: latency, success rate, token usage, cost estimation, JSON validity
"""

import asyncio
import json
import os
import time
from dataclasses import dataclass, asdict
from typing import List, Optional
import httpx
from dotenv import load_dotenv

load_dotenv()

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

if not NVIDIA_API_KEY:
    raise ValueError("NVIDIA_API_KEY not set in environment")

# Extended candidate models list
CANDIDATE_MODELS = [
    "nvidia/nemotron-3-super-120b-a12b",
    "nvidia/nemotron-3-nano-30b-a3b",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
    "openai/gpt-oss-120b",
    "qwen/qwen3-next-80b-a3b-instruct",
    "mistralai/mistral-small-3.1-24b-instruct-2503",
    "google/gemma-3-27b-it",
    "deepseek-ai/deepseek-v3.2",
]

TEST_PROMPTS = [
    "What is the capital of France?",
    "Explain quantum computing in simple terms.",
    "Write a Python function to calculate fibonacci numbers.",
]

# JSON structured output test prompt
JSON_TEST_PROMPT = """Return a JSON object with exactly these fields: {"name": "string", "age": "integer", "skills": "array of strings", "active": "boolean"}. Example: {"name": "John", "age": 30, "skills": ["Python", "SQL"], "active": true}. Return ONLY the JSON, no extra text."""

NUM_CALLS_PER_MODEL = 3
REQUEST_TIMEOUT = 60.0


@dataclass
class CallResult:
    model: str
    prompt: str
    success: bool
    latency_ms: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    error: str = ""
    response_preview: str = ""
    json_valid: bool = False


@dataclass
class ModelSummary:
    model: str
    total_calls: int
    successful_calls: int
    success_rate: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    json_tests: int = 0
    json_passed: int = 0
    json_pass_rate: float = 0.0


async def call_model(client: httpx.AsyncClient, model: str, prompt: str, test_json: bool = False) -> CallResult:
    """Make a single call to the model and return results."""
    start = time.perf_counter()

    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 512,
    }

    try:
        response = await client.post(
            f"{NVIDIA_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        latency_ms = (time.perf_counter() - start) * 1000

        if response.status_code == 200:
            data = response.json()
            usage = data.get("usage", {})
            content = data["choices"][0]["message"]["content"]

            # Test JSON validity if requested
            json_valid = False
            if test_json:
                try:
                    parsed = json.loads(content.strip())
                    # Check required fields
                    required = {"name", "age", "skills", "active"}
                    if all(k in parsed for k in required):
                        json_valid = True
                except json.JSONDecodeError:
                    json_valid = False

            return CallResult(
                model=model,
                prompt=prompt,
                success=True,
                latency_ms=latency_ms,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                response_preview=content[:100] + "..." if len(content) > 100 else content,
                json_valid=json_valid,
            )
        else:
            error_text = response.text
            return CallResult(
                model=model,
                prompt=prompt,
                success=False,
                latency_ms=latency_ms,
                error=f"HTTP {response.status_code}: {error_text}",
            )
    except httpx.TimeoutException:
        latency_ms = (time.perf_counter() - start) * 1000
        return CallResult(
            model=model,
            prompt=prompt,
            success=False,
            latency_ms=latency_ms,
            error="Timeout",
        )
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        return CallResult(
            model=model,
            prompt=prompt,
            success=False,
            latency_ms=latency_ms,
            error=str(e),
        )


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate cost in USD based on model pricing (approximate)."""
    # Rough pricing per 1M tokens (input/output) - these are estimates
    pricing = {
        "nvidia/nemotron-3-super-120b-a12b": (0.50, 0.50),
        "nvidia/nemotron-3-nano-30b-a3b": (0.10, 0.10),
        "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning": (0.15, 0.15),
        "openai/gpt-oss-120b": (0.50, 0.50),
        "qwen/qwen3-next-80b-a3b-instruct": (0.30, 0.30),
        "mistralai/mistral-small-3.1-24b-instruct-2503": (0.20, 0.20),
        "google/gemma-3-27b-it": (0.15, 0.15),
        "deepseek-ai/deepseek-v3.2": (0.25, 0.25),
    }
    input_price, output_price = pricing.get(model, (0.50, 0.50))
    return (prompt_tokens * input_price + completion_tokens * output_price) / 1_000_000


async def benchmark_model(model: str) -> List[CallResult]:
    """Run benchmark for a single model across all prompts + JSON test."""
    print(f"\n{'='*60}")
    print(f"Benchmarking: {model}")
    print(f"{'='*60}")

    results = []
    async with httpx.AsyncClient() as client:
        # Regular prompts
        for i, prompt in enumerate(TEST_PROMPTS):
            for call_num in range(NUM_CALLS_PER_MODEL):
                print(f"  Call {call_num + 1}/{NUM_CALLS_PER_MODEL} - Prompt {i + 1}/{len(TEST_PROMPTS)}: {prompt[:50]}...")
                result = await call_model(client, model, prompt)
                results.append(result)
                status = "OK" if result.success else "FAIL"
                print(f"    {status} {result.latency_ms:.0f}ms - {result.error or 'OK'}")
                await asyncio.sleep(0.5)

        # JSON structured output test
        print(f"  JSON structured output test...")
        json_result = await call_model(client, model, JSON_TEST_PROMPT, test_json=True)
        results.append(json_result)
        status = "OK" if json_result.success else "FAIL"
        json_status = "JSON_OK" if json_result.json_valid else "JSON_FAIL"
        print(f"    {status} {json_result.latency_ms:.0f}ms - {json_status} - {json_result.error or 'OK'}")
        await asyncio.sleep(0.5)
    return results


def summarize_results(all_results: List[CallResult]) -> List[ModelSummary]:
    """Summarize results by model."""
    summaries = []
    for model in CANDIDATE_MODELS:
        model_results = [r for r in all_results if r.model == model]
        successful = [r for r in model_results if r.success]

        if not model_results:
            continue

        total_calls = len(model_results)
        successful_calls = len(successful)
        success_rate = successful_calls / total_calls if total_calls > 0 else 0

        latencies = [r.latency_ms for r in successful]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        min_latency = min(latencies) if latencies else 0
        max_latency = max(latencies) if latencies else 0

        total_prompt_tokens = sum(r.prompt_tokens for r in successful)
        total_completion_tokens = sum(r.completion_tokens for r in successful)
        total_tokens = sum(r.total_tokens for r in successful)

        estimated_cost = estimate_cost(model, total_prompt_tokens, total_completion_tokens)

        # JSON test stats
        json_tests = [r for r in model_results if r.prompt == JSON_TEST_PROMPT]
        json_passed = sum(1 for r in json_tests if r.json_valid)
        json_pass_rate = json_passed / len(json_tests) if json_tests else 0.0

        summaries.append(ModelSummary(
            model=model,
            total_calls=total_calls,
            successful_calls=successful_calls,
            success_rate=success_rate,
            avg_latency_ms=avg_latency,
            min_latency_ms=min_latency,
            max_latency_ms=max_latency,
            total_prompt_tokens=total_prompt_tokens,
            total_completion_tokens=total_completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost,
            json_tests=len(json_tests),
            json_passed=json_passed,
            json_pass_rate=json_pass_rate,
        ))
    return summaries


def print_summary_table(summaries: List[ModelSummary]):
    """Print a formatted summary table."""
    print(f"\n{'='*140}")
    print("BENCHMARK SUMMARY")
    print(f"{'='*140}")
    print(f"{'Model':<45} {'Calls':>5} {'Succ':>4} {'Rate':>6} {'Avg(ms)':>8} {'Min(ms)':>8} {'Max(ms)':>8} {'Tokens':>10} {'Cost($)':>10} {'JSON':>4} {'J%':>6}")
    print(f"{'-'*140}")

    for s in summaries:
        json_str = f"{s.json_passed}/{s.json_tests}"
        print(f"{s.model:<45} {s.total_calls:>5} {s.successful_calls:>4} {s.success_rate:>6.0%} {s.avg_latency_ms:>8.0f} {s.min_latency_ms:>8.0f} {s.max_latency_ms:>8.0f} {s.total_tokens:>10} {s.estimated_cost_usd:>10.4f} {json_str:>4} {s.json_pass_rate:>6.0%}")

    print(f"{'-'*140}")

    # Filter out failed models (404/410/503)
    working_models = [s for s in summaries if s.success_rate > 0]
    failed_models = [s for s in summaries if s.success_rate == 0]

    if failed_models:
        print(f"\nEXCLUDED MODELS (404/410/503/timeout):")
        for s in failed_models:
            print(f"  {s.model}")

    # Best model recommendations
    if working_models:
        fastest = min(working_models, key=lambda s: s.avg_latency_ms)
        most_reliable = max(working_models, key=lambda s: s.success_rate)
        cheapest = min(working_models, key=lambda s: s.estimated_cost_usd)
        best_json = max(working_models, key=lambda s: s.json_pass_rate)

        print(f"\nRECOMMENDATIONS:")
        print(f"  Fastest (avg latency):     {fastest.model} ({fastest.avg_latency_ms:.0f}ms)")
        print(f"  Most reliable (success%):  {most_reliable.model} ({most_reliable.success_rate:.0%})")
        print(f"  Cheapest (estimated):      {cheapest.model} (${cheapest.estimated_cost_usd:.4f})")
        print(f"  Best JSON output:          {best_json.model} ({best_json.json_pass_rate:.0%})")


def save_results(all_results: List[CallResult], summaries: List[ModelSummary]):
    """Save detailed results to JSON file."""
    output = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "config": {
            "models_tested": CANDIDATE_MODELS,
            "prompts": TEST_PROMPTS,
            "json_test_prompt": JSON_TEST_PROMPT,
            "calls_per_model_per_prompt": NUM_CALLS_PER_MODEL,
        },
        "detailed_results": [asdict(r) for r in all_results],
        "summaries": [asdict(s) for s in summaries],
    }

    output_path = "scripts/benchmark_results.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nDetailed results saved to: {output_path}")


async def main():
    print("NIM Sentinel - Model Benchmark")
    total_calls = len(CANDIDATE_MODELS) * (len(TEST_PROMPTS) * NUM_CALLS_PER_MODEL + 1)
    print(f"Testing {len(CANDIDATE_MODELS)} models x ({len(TEST_PROMPTS)} prompts x {NUM_CALLS_PER_MODEL} calls + 1 JSON test) = {total_calls} total calls")

    all_results = []
    for model in CANDIDATE_MODELS:
        results = await benchmark_model(model)
        all_results.extend(results)

    summaries = summarize_results(all_results)
    print_summary_table(summaries)
    save_results(all_results, summaries)

    # Exit with error code if all models failed
    if all(s.success_rate == 0 for s in summaries):
        print("\n[FAIL] ALL MODELS FAILED - Check API key and network")
        return 1

    print("\n[OK] Benchmark complete")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
#!/usr/bin/env python
"""
Benchmark script to test LLM candidates for NIM Sentinel.
Tests 4 candidate models with 3 calls each:
- meta/llama-3.3-70b-instruct
- meta/llama-3.1-70b-instruct
- meta/llama-3.1-8b-instruct
- nvidia/nemotron-3-ultra-550b-a55b

Measures: latency, success rate, token usage, cost estimation
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

CANDIDATE_MODELS = [
    "meta/llama-3.3-70b-instruct",
    "meta/llama-3.1-70b-instruct",
    "meta/llama-3.1-8b-instruct",
    "nvidia/nemotron-3-ultra-550b-a55b",
]

TEST_PROMPTS = [
    "What is the capital of France?",
    "Explain quantum computing in simple terms.",
    "Write a Python function to calculate fibonacci numbers.",
]

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


async def call_model(client: httpx.AsyncClient, model: str, prompt: str) -> CallResult:
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
            return CallResult(
                model=model,
                prompt=prompt,
                success=True,
                latency_ms=latency_ms,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                response_preview=content[:100] + "..." if len(content) > 100 else content,
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
        "meta/llama-3.3-70b-instruct": (0.59, 0.79),
        "meta/llama-3.1-70b-instruct": (0.59, 0.79),
        "meta/llama-3.1-8b-instruct": (0.06, 0.06),
        "nvidia/nemotron-3-ultra-550b-a55b": (1.00, 1.00),  # Premium model estimate
    }
    input_price, output_price = pricing.get(model, (0.50, 0.50))
    return (prompt_tokens * input_price + completion_tokens * output_price) / 1_000_000


async def benchmark_model(model: str) -> List[CallResult]:
    """Run benchmark for a single model across all prompts."""
    print(f"\n{'='*60}")
    print(f"Benchmarking: {model}")
    print(f"{'='*60}")

    results = []
    async with httpx.AsyncClient() as client:
        for i, prompt in enumerate(TEST_PROMPTS):
            for call_num in range(NUM_CALLS_PER_MODEL):
                print(f"  Call {call_num + 1}/{NUM_CALLS_PER_MODEL} - Prompt {i + 1}/{len(TEST_PROMPTS)}: {prompt[:50]}...")
                result = await call_model(client, model, prompt)
                results.append(result)
                status = "OK" if result.success else "FAIL"
                print(f"    {status} {result.latency_ms:.0f}ms - {result.error or 'OK'}")
                # Small delay between calls to avoid rate limiting
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
        ))
    return summaries


def print_summary_table(summaries: List[ModelSummary]):
    """Print a formatted summary table."""
    print(f"\n{'='*120}")
    print("BENCHMARK SUMMARY")
    print(f"{'='*120}")
    print(f"{'Model':<40} {'Calls':>5} {'Success':>7} {'Rate':>6} {'Avg(ms)':>8} {'Min(ms)':>8} {'Max(ms)':>8} {'Tokens':>10} {'Cost($)':>10}")
    print(f"{'-'*120}")

    for s in summaries:
        print(f"{s.model:<40} {s.total_calls:>5} {s.successful_calls:>7} {s.success_rate:>6.0%} {s.avg_latency_ms:>8.0f} {s.min_latency_ms:>8.0f} {s.max_latency_ms:>8.0f} {s.total_tokens:>10} {s.estimated_cost_usd:>10.4f}")

    print(f"{'-'*120}")

    # Best model recommendations
    successful_summaries = [s for s in summaries if s.success_rate > 0]
    if successful_summaries:
        fastest = min(successful_summaries, key=lambda s: s.avg_latency_ms)
        most_reliable = max(successful_summaries, key=lambda s: s.success_rate)
        cheapest = min(successful_summaries, key=lambda s: s.estimated_cost_usd)

        print(f"\nRECOMMENDATIONS:")
        print(f"  Fastest (avg latency):     {fastest.model} ({fastest.avg_latency_ms:.0f}ms)")
        print(f"  Most reliable (success%):  {most_reliable.model} ({most_reliable.success_rate:.0%})")
        print(f"  Cheapest (estimated):      {cheapest.model} (${cheapest.estimated_cost_usd:.4f})")


def save_results(all_results: List[CallResult], summaries: List[ModelSummary]):
    """Save detailed results to JSON file."""
    output = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "config": {
            "models_tested": CANDIDATE_MODELS,
            "prompts": TEST_PROMPTS,
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
    print(f"Testing {len(CANDIDATE_MODELS)} models x {len(TEST_PROMPTS)} prompts x {NUM_CALLS_PER_MODEL} calls = {len(CANDIDATE_MODELS) * len(TEST_PROMPTS) * NUM_CALLS_PER_MODEL} total calls")

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
# Kubernetes Benchmark Suite for Llama Stack

Benchmark performance between Llama Stack and vLLM direct inference on Kubernetes.

## Setup

**1. Deploy base k8s infrastructure:**
```bash
cd ../k8s
./apply.sh
```

**2. Deploy benchmark components:**
```bash
cd ../k8s-benchmark
./apply.sh
```

**3. Verify deployment:**
```bash
kubectl get pods
# Should see: llama-stack-benchmark-server, vllm-server, etc.
```

## Quick Start

### Basic Benchmarks

**Benchmark Llama Stack (default):**
```bash
cd docs/source/distributions/k8s-benchmark/
./run-benchmark.sh
```

**Benchmark vLLM direct:**
```bash
./run-benchmark.sh --target vllm
```

### Custom Configuration

**Extended benchmark with high concurrency:**
```bash
./run-benchmark.sh --target vllm --duration 120 --concurrent 20
```

**Short test run:**
```bash
./run-benchmark.sh --target stack --duration 30 --concurrent 5
```

## Command Reference

### run-benchmark.sh Options

```bash
./run-benchmark.sh [options]

Options:
  -t, --target <stack|vllm>     Target to benchmark (default: stack)
  -d, --duration <seconds>      Duration in seconds (default: 60)
  -c, --concurrent <users>      Number of concurrent users (default: 10)
  -h, --help                    Show help message

Examples:
  ./run-benchmark.sh --target vllm              # Benchmark vLLM direct
  ./run-benchmark.sh --target stack             # Benchmark Llama Stack
  ./run-benchmark.sh -t vllm -d 120 -c 20       # vLLM with 120s, 20 users
```

## Local Testing

### Running Benchmark Locally

For local development without Kubernetes:

**1. Start OpenAI mock server:**
```bash
uv run python openai-mock-server.py --port 8080
```

**2. Run benchmark against mock server:**
```bash
uv run python benchmark.py \
  --base-url http://localhost:8080/v1 \
  --model mock-inference \
  --duration 30 \
  --concurrent 5
```

**3. Test against local vLLM server:**
```bash
# If you have vLLM running locally on port 8000
uv run python benchmark.py \
  --base-url http://localhost:8000/v1 \
  --model meta-llama/Llama-3.2-3B-Instruct \
  --duration 30 \
  --concurrent 5
```

**4. Profile the running server:**
```bash
./profile_running_server.sh
```



### OpenAI Mock Server

The `openai-mock-server.py` provides:
- **OpenAI-compatible API** for testing without real models
- **Configurable streaming delay** via `STREAM_DELAY_SECONDS` env var
- **Consistent responses** for reproducible benchmarks
- **Lightweight testing** without GPU requirements

**Mock server usage:**
```bash
uv run python openai-mock-server.py --port 8080
```

The mock server is also deployed in k8s as `openai-mock-service:8080` and can be used by changing the Llama Stack configuration to use the `mock-vllm-inference` provider.

## Files in this Directory

- `benchmark.py` - Core benchmark script with async streaming support
- `run-benchmark.sh` - Main script with target selection and configuration
- `openai-mock-server.py` - Mock OpenAI API server for local testing
- `README.md` - This documentation file

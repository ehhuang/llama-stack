#!/bin/bash
set -e

stack_config="$1"
inference_mode="$2"
provider="$3"
run_vision_tests="$4"
test_types="$5"

EXCLUDE_TESTS="builtin_tool or safety_with_image or code_interpreter or test_rag"

# Configure provider-specific settings
if [ "$provider" == "ollama" ]; then
  EXTRA_PARAMS="--safety-shield=llama-guard"
else
  EXTRA_PARAMS=""
  EXCLUDE_TESTS="${EXCLUDE_TESTS} or test_inference_store_tool_calls"
fi

if [ "$run_vision_tests" == "true" ]; then
  if uv run pytest -s -v tests/integration/inference/test_vision_inference.py --stack-config=${stack_config} \
    -k "not( ${EXCLUDE_TESTS} )" \
    --vision-model=ollama/llama3.2-vision:11b \
    --embedding-model=sentence-transformers/all-MiniLM-L6-v2 \
    --color=yes ${EXTRA_PARAMS} \
    --capture=tee-sys | tee pytest-${inference_mode}-vision.log; then
    echo "✅ Tests completed for vision"
  else
    echo "❌ Tests failed for vision"
    exit 1
  fi
  exit 0
fi

# Run non-vision tests
echo "Test types to run: $test_types"

# Collect all test files for the specified test types
TEST_FILES=""
for test_type in $(echo "$test_types" | jq -r '.[]'); do
  # if provider is vllm, exclude the following tests: (safety, post_training, tool_runtime)
  if [ "$provider" == "vllm" ]; then
    if [ "$test_type" == "safety" ] || [ "$test_type" == "post_training" ] || [ "$test_type" == "tool_runtime" ]; then
      echo "Skipping $test_type for vllm provider"
      continue
    fi
  fi

  if [ -d "tests/integration/$test_type" ]; then
    # Find all Python test files in this directory
    test_files=$(find tests/integration/$test_type -name "test_*.py" -o -name "*_test.py")
    if [ -n "$test_files" ]; then
      TEST_FILES="$TEST_FILES $test_files"
      echo "Added test files from $test_type: $(echo $test_files | wc -w) files"
    fi
  else
    echo "Warning: Directory tests/integration/$test_type does not exist"
  fi
done

if [ -z "$TEST_FILES" ]; then
  echo "No test files found for the specified test types"
  exit 1
fi

echo "=== Running all collected tests in a single pytest command ==="
echo "Total test files: $(echo $TEST_FILES | wc -w)"

PYTEST_CMD="uv run pytest -s -v $TEST_FILES \
  --stack-config=${stack_config} \
  -k \"not( ${EXCLUDE_TESTS} )\" \
  --text-model=$TEXT_MODEL \
  --embedding-model=sentence-transformers/all-MiniLM-L6-v2 \
  --color=yes \
  ${EXTRA_PARAMS} \
  --capture=tee-sys | tee pytest-${inference_mode}-all.log"

echo "Running: $PYTEST_CMD"
if eval "$PYTEST_CMD"; then
  echo "✅ All tests completed successfully"
else
  echo "❌ Tests failed"
  exit 1
fi
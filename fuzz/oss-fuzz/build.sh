#!/bin/bash -eu
# OSS-Fuzz build script for Hancock

# Install project dependencies so fuzz targets can import modules
pip3 install -r "$SRC/hancock/requirements.txt"

# Compile each fuzz target using the OSS-Fuzz Python helper
FUZZ_DIR="$SRC/hancock/fuzz"

for fuzzer in "$FUZZ_DIR"/fuzz_*.py; do
    fuzzer_basename=$(basename "$fuzzer" .py)

    # Compile the fuzzer
    compile_python_fuzzer "$fuzzer"

    # Copy seed corpus if it exists
    corpus_name="${fuzzer_basename#fuzz_}"
    corpus_dir="$FUZZ_DIR/corpus/$corpus_name"
    if [ -d "$corpus_dir" ]; then
        zip -j "$OUT/${fuzzer_basename}_seed_corpus.zip" "$corpus_dir"/* 2>/dev/null || true
    fi
done

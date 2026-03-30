#!/bin/bash -eu
# OSS-Fuzz build script for Hancock
# Docs: https://google.github.io/oss-fuzz/getting-started/new-project-guide/python-lang/

# Install project dependencies so fuzz targets can import modules
pip3 install -r "$SRC/hancock/requirements.txt"

# Ensure the project root is on PYTHONPATH so fuzz targets can import
# Hancock modules (collectors, formatter, etc.) without install.
export PYTHONPATH="$SRC/hancock:${PYTHONPATH:-}"

# Compile each fuzz target using the OSS-Fuzz Python helper
FUZZ_DIR="$SRC/hancock/fuzz"

for fuzzer in "$FUZZ_DIR"/fuzz_*.py; do
    [ -e "$fuzzer" ] || continue          # guard against empty glob
    fuzzer_basename=$(basename "$fuzzer" .py)

    # compile_python_fuzzer is provided by base-builder-python
    compile_python_fuzzer "$fuzzer"

    # Copy seed corpus if it exists
    corpus_name="${fuzzer_basename#fuzz_}"
    corpus_dir="$FUZZ_DIR/corpus/$corpus_name"
    if [ -d "$corpus_dir" ]; then
        zip -j "$OUT/${fuzzer_basename}_seed_corpus.zip" "$corpus_dir"/* 2>/dev/null || true
    fi
done

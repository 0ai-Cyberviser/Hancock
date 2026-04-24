#!/bin/bash
pip install -r requirements.txt
python -m pyright .  # type safety
python -m pytest tests/ -q --tb=no
python -m clusterfuzzlite build --engine=atheris --language=python
echo "✅ ClusterFuzzLite build complete"

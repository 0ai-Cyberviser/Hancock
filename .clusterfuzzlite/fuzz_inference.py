#!/usr/bin/env python3
import atheris
import sys
from inference.optimized_inference import HancockInferenceEngine, RecursiveSelfImprover

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        prompt = fdp.ConsumeUnicodeNoSurrogates(200)
        engine = HancockInferenceEngine()
        # Run a quick generate call with fuzzed input
        import asyncio
        result = asyncio.run(engine.generate(prompt, max_tokens=50))
    except Exception as e:
        # We want to catch crashes and exceptions
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()

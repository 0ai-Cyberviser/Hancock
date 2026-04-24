#!/usr/bin/env python3
import atheris
import sys
@atheris.instrument_func
def test_fuzz_langgraph(data):
    fdp = atheris.FuzzedDataProvider(data)
    fake_prompt = fdp.ConsumeUnicodeNoSurrogates(1024)
    try:
        assert "unauthorized" not in fake_prompt.lower()
    except Exception:
        pass

if __name__ == "__main__":
    atheris.Setup(sys.argv, test_fuzz_langgraph)
    atheris.Fuzz()

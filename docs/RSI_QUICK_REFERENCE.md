# Hancock Recursive Self-Improvement (RSI) - Quick Reference

## 🚀 One-Minute Overview

Hancock RSI is a **safety-bounded autonomous improvement engine** that:
1. Measures capabilities (test coverage, accuracy, security patterns, etc.)
2. Identifies gaps between current and target performance
3. Generates code improvement proposals
4. Validates via security checks + automated testing
5. Executes approved changes (human-in-the-loop)
6. Feeds training data back into PeachTree

**Safety Guarantees:** No eval/exec, no autonomous deployment, human approval for critical changes, full audit trail.

---

## ⚡ Commands

### Assess Current State (Read-Only)
```bash
python hancock_rsi.py --assess-only
```

### Run 1 RSI Cycle
```bash
python hancock_rsi.py --max-iterations 1
```

### Run Full Loop (Until Targets Met)
```bash
python hancock_rsi.py --max-iterations 100
```

### Run Tests
```bash
pytest tests/test_hancock_rsi.py -v
```

---

## 📊 Capability Targets

| Capability | Current | Target | Status |
|-----------|---------|--------|--------|
| Test Coverage | 85% | 95% | ⚠️ Below |
| Response Accuracy | 82% | 92% | ⚠️ Below |
| Dataset Quality | 88% | 95% | ⚠️ Below |
| Security Patterns | 34 | 50 | ⚠️ Below |
| Collector Freshness | 24h | 6h | ⚠️ Below |

---

## 🔒 Security Policy

**Forbidden Operations (always blocked):**
- `os.system()`, `subprocess.Popen()`
- `eval()`, `exec()`, `__import__()`
- `rm -rf`, unencrypted HTTP calls
- Non-atomic file writes

**Approval Requirements:**
- NEW_FEATURE → Human required
- SECURITY_ENHANCEMENT → Human required  
- CODE_OPTIMIZATION → Auto if tests pass
- DOCUMENTATION → Auto if tests pass

---

## 📝 Proposal Lifecycle

```
Generate → Security Check → Test Suite → Regression Check → Human Review → Execute
```

**Rejection Criteria:**
- Forbidden operation detected
- Test failures
- Capability degrades >5%
- Human rejects

---

## 📈 Key Metrics

**Success Rate:** approved / generated  
**Target:** >70%

**Test Pass Rate:** tests passing / total  
**Target:** >95%

**Dataset Records:** Training pairs generated from RSI  
**Target:** 100+ per week

---

## 🧪 Example Workflow

```bash
# 1. Check current state
python hancock_rsi.py --assess-only

Output:
✅ test_coverage: 0.91 / 0.95
⚠️ security_pattern_coverage: 34.00 / 50.00

# 2. Run one cycle
python hancock_rsi.py --max-iterations 1

Output:
Cycle 1: Generated 3 proposals
- Proposal a3f9c2: "Expand security patterns" → REQUIRES HUMAN REVIEW
- Proposal b2e7d1: "Add unit tests" → PASSED → EXECUTED
- Proposal c8a4f3: "Update docs" → PASSED → EXECUTED

# 3. Review proposals
cat .hancock_rsi_history.jsonl | jq '.proposals[] | select(.validation_status == "requires_human_review")'

# 4. Approve manually (edit code, run tests, commit)
git add src/peachtree/safety.py
git commit -m "feat: Add Azure/GCP secret patterns (RSI proposal a3f9c2)"

# 5. Next cycle automatically picks up improvements
```

---

## 🔧 Configuration

**Environment Variables:**
```bash
export HANCOCK_WORKSPACE=/home/_0ai_/Hancock-1
export PEACHTREE_PATH=/home/_0ai_/PeachTree
export RSI_MAX_ITERATIONS=10
export RSI_AUTO_APPROVE=false  # Never true in production
```

**Python API:**
```python
from hancock_rsi import RecursiveSelfImprover

rsi = RecursiveSelfImprover(
    workspace="/path/to/Hancock",
    peachtree_path="/path/to/PeachTree",
    max_iterations=10,
    require_human_approval=True,  # Always True in production
)

# Assess only
capabilities = rsi.assess_capabilities()

# Run full loop
metrics = rsi.run()
print(f"Success rate: {metrics['success_rate']:.2%}")
```

---

## 🛡️ Safety Checklist

Before enabling RSI in production:
- [ ] Human approval enabled (`require_human_approval=True`)
- [ ] Security policy validated (no forbidden ops)
- [ ] Test suite passing (>95% coverage)
- [ ] Audit trail configured (`.hancock_rsi_history.jsonl`)
- [ ] Rollback procedure documented
- [ ] Alert system for failed proposals
- [ ] Code review for all executed proposals

---

## 🐛 Troubleshooting

**Problem:** RSI generates no proposals  
**Solution:** Check that capabilities are below targets (`--assess-only`)

**Problem:** All proposals fail security check  
**Solution:** Review `SecurityPolicy.FORBIDDEN_OPERATIONS` - may be too strict

**Problem:** Tests fail during validation  
**Solution:** Ensure baseline tests pass before running RSI (`make test`)

**Problem:** Capabilities regress  
**Solution:** Check `.hancock_rsi_history.jsonl` for failed proposals, review changes

**Problem:** History file grows too large  
**Solution:** Archive old entries: `mv .hancock_rsi_history.jsonl history_backup_$(date +%Y%m%d).jsonl`

---

## 📚 Learn More

- Full documentation: `docs/RSI_FRAMEWORK.md`
- Test suite: `tests/test_hancock_rsi.py`
- Source code: `hancock_rsi.py`
- Research: Voyager, STOP, Self-Rewarding LLMs, AlphaEvolve

---

**Status:** Production-ready with human-in-the-loop control  
**Author:** HancockForge / AssuranceForge  
**License:** Same as Hancock project

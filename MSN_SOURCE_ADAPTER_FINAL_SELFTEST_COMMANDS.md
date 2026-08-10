# MSN Final Self-Test Commands

## Repository-wide MSN self-test orchestration

```cmd
python source_msn_adapter_final_selftest_orchestrator.py --repo . --out reports\msn_final_selftests --fail-fast
```

## Full discovery without fail-fast

```cmd
python source_msn_adapter_final_selftest_orchestrator.py --repo . --out reports\msn_final_selftests_full
```

## Selected final gate tests only

```cmd
python source_msn_adapter_final_selftest_orchestrator.py --repo . --pattern source_msn_adapter_release_candidate_lock_test.py --pattern source_msn_adapter_live_evidence_validator_test.py --pattern source_msn_adapter_release_promotion_test.py --pattern source_msn_adapter_user_goal_traceability_test.py --pattern source_msn_adapter_final_signoff_gate_test.py --out reports\msn_final_gate_selftests --fail-fast
```

## Interpretation

Passing these commands means the repository self-tests are consistent. It does not mean the MSN adapter has been live-certified against a real MSN page. Live completion still requires positive manual/live evidence and the existing certification/signoff tools.

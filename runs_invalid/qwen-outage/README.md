# Runs set aside: Qwen endpoint outage (8 Nov 2026)

Adaption's qwen3.8-27b endpoint returned gateway time-outs from about 16:00 IST on 8 Nov 2026. These 25 runs
finished before the fallback to qwen3.5-397b was added, so more than 5% of their fresh agent turns failed (the
two Qwen agents' turns, about 22%): those agents posted nothing and kept runs by the default rule. They were
re-run under the same names with the fallback; the re-runs replaced them in runs/. Kept here for the record.

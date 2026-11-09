#!/bin/zsh
# Run all four stages; retain failures and return nonzero if any stage failed.
# Rerunning appends a new session. It does not resume an interrupted measurement.
cd "$(dirname "$0")"
N="RTX 3080 12GB stock 390W, 32GB DDR4, Windows, run from Mac over LAN"
ladder_rc=0
run_step() {
    ./bench.py "$@"
    local step_rc=$?
    if (( step_rc == 130 || step_rc == 143 )); then
        exit "$step_rc"
    fi
    if (( step_rc != 0 )); then
        ladder_rc=1
    fi
}
run_step -g moe   --pull --runs 3 --note "$N"
run_step -g quant --pull --runs 3 --note "$N"
run_step -g quant -m qwen2.5:14b --ctx 2048,8192,16384,32768 --runs 3 --note "$N"
run_step -g moe   -m qwen3:30b-a3b --ctx 2048,8192,16384,32768 --runs 3 --note "$N"
echo "LADDER-DONE rc=$ladder_rc"
exit "$ladder_rc"

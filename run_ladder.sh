#!/bin/zsh
# The whole ladder/MoE session, in order of how much the result matters. Resumable: --pull skips what is on the PC.
cd "$(dirname "$0")"
N="RTX 3080 12GB stock 390W, 32GB DDR4, Windows, run from Mac over LAN"
./bench.py -g moe   --pull --note "$N" && \
./bench.py -g quant --pull --note "$N" && \
./bench.py -g quant -m qwen2.5:14b --ctx 2048,8192,16384,32768 --note "$N" && \
./bench.py -g moe   -m qwen3:30b-a3b --ctx 2048,8192,16384,32768 --note "$N"
echo "LADDER-DONE rc=$?"

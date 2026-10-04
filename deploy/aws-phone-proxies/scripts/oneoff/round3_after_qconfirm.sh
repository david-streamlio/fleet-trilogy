#!/bin/bash
while pgrep -f "/Users/ec2-user/phoneproxy/[b]ench_quant_confirm.sh" >/dev/null; do sleep 60; done
exec /Users/ec2-user/phoneproxy/bench_round3.sh /Users/ec2-user/phoneproxy /Users/ec2-user/fleet-trilogy 2

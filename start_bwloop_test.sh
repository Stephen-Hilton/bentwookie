cd ./test/init_test
while :; do bw --next_prompt "game builder" --tasks "./tasks" --logs "./logs/{date}.log" | claude --dangerously-skip-permissions ; done``
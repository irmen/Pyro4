#!/usr/bin/env bash

python -m Pyro4.naming &
sleep 0.5

NUM_CPUS=$(python -c "import os; print(os.cpu_count())")

echo "Launching ${NUM_CPUS} mandelbrot server processes..."
for id in $(seq 1 ${NUM_CPUS})
do
    python server.py ${id} &
done

sleep 1
echo ""
echo "Now start a client."

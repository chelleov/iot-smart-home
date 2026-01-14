#!/bin/bash

# Launch all IoT GUI applications
cd /home/chelle/Projects/iot-smart-home/scripts/cubes_test

PYTHON_CMD="/home/chelle/Projects/iot-smart-home/scripts/cubes_test/.venv/bin/python"

# Launch each application in the background
$PYTHON_CMD client.py &
$PYTHON_CMD DHT.py &
$PYTHON_CMD BUTTON.py &
$PYTHON_CMD RELAY.py &

echo "All applications launched!"
echo "Close this terminal to stop all applications."
wait

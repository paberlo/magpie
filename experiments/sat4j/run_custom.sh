#!/bin/bash

# # Ensure the script is run with the necessary arguments
# if [ "$#" -ne 1 ]; then
#     echo "Usage: $0 <command> "
#      echo "You provided the following arguments: $@"
#     echo "Number of arguments: $#"

#     exit 1
# fi

# Assign arguments to variables
command="$*"

taskset -c 0 timeout 60s perf record  -g -F 1000  -e cycles:u -- $command

# Check the exit status of the timeout command
if [ $? -eq 124 ]; then
  echo "Program did not finish in 40 seconds and was terminated."
  #python3 read_total.py error
  exit 1
else
  echo "Program finished within the time limit."
  perf report  --stdio > report1.txt
  perf annotate --stdio > report2.txt
  python3 read_total.py report1.txt report2.txt
fi



#echo "All files have been created."

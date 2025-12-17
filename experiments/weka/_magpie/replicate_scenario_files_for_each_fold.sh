#!/bin/bash

# Check that exactly 3 arguments are provided
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <file_with_FOLD1> <K> <steps>"
    exit 1
fi

# Input parameters
INPUT_FILE=$1
K=$2
STEPS=$3

# Check if the input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: The file $INPUT_FILE does not exist."
    exit 1
fi

# Extract file name and ensure it contains "FOLD1"
BASENAME=$(basename "$INPUT_FILE" .txt)

if [[ "$BASENAME" != *"FOLD1" ]]; then
    echo "Error: The input file name must end with 'FOLD1'."
    exit 1
fi

# Remove "1" from the name (e.g., FOLD1 -> FOLD)
PREFIX=${BASENAME%1}

# Loop to create K scenario files
for i in $(seq 1 "$K"); do
    # Generate the FOLD file name replacing the number and adding _steps<STEPS>
    FOLD_FILE="${PREFIX}${i}_steps${STEPS}.txt"
    cp "$INPUT_FILE" "$FOLD_FILE"

    # Replace content for FOLD<i> and steps
    sed -i "s/log_suffix_label = FOLD[0-9]*/log_suffix_label = FOLD${i}/g" "$FOLD_FILE"

    # Ensure that the comment for FOLD is unique
    sed -i -E "s/# FOLD [0-9]+( for kfold CV)*$/# FOLD ${i} for kfold CV/g" "$FOLD_FILE"

    sed -i "s/run_cmd = bash run.sh [0-9]*/run_cmd = bash run.sh ${i}/g" "$FOLD_FILE"
    sed -i "s/max_steps = [0-9]*/max_steps = ${STEPS}/g" "$FOLD_FILE"

    echo "Created FOLD file: $FOLD_FILE"
done
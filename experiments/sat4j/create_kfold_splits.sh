#!/usr/bin/env bash

SEED=1
#script to be called before running an scenario
# K is the number of folds to create for cross-validation
K=$1


# Ensure exact one argument (K value) is provided
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 K"
    exit 1
fi


DATA_DIR="data"
TRAIN_PREFIX="train"
VALIDATE_PREFIX="validate"

# List all .cnf files in the data directory and verify they exist
FILES=$(find "$DATA_DIR" -maxdepth 1 -name "*.cnf" | sort)
if [ -z "$FILES" ]; then
    echo "Error: No .cnf files found in directory $DATA_DIR."
    exit 1
fi

# Count total .cnf files
TOTAL_FILES=$(echo "$FILES" | wc -l)

# Verify that the number of files is enough for K partitions
if [ "$TOTAL_FILES" -lt "$K" ]; then
    echo "Error: Number of .cnf files ($TOTAL_FILES) is less than K ($K)."
    exit 1
fi

# Shuffle the list of files to ensure random assignment
yes "1" | tr -d '\n' | head -c 1024 > seed.txt
echo $SEED | sha256sum | head -c 1024 > seed.txt
SHUFFLED_FILES=$(echo "$FILES" | shuf --random-source=seed.txt)
rm seed.txt

# Calculate the number of files per training fold (rounded up)
FILES_PER_GROUP=$(( (TOTAL_FILES + K - 1) / K ))

# Clean up any previously created train and validate files
rm -f "$DATA_DIR/$TRAIN_PREFIX"* "$DATA_DIR/$VALIDATE_PREFIX"* 2> /dev/null

# Convert the shuffled file list into an array for easy access
SHUFFLED_ARRAY=( $SHUFFLED_FILES )

# Create train and validate files
for ((i = 0; i < K; i++)); do
    TRAIN_FILE="$DATA_DIR/${TRAIN_PREFIX}$((i + 1))"
    VALIDATE_FILE="$DATA_DIR/${VALIDATE_PREFIX}$((i + 1))"

    echo "Creating $TRAIN_FILE and $VALIDATE_FILE..."

    # Calculate the start and end indices for train group 'i'
    START=$(( i * FILES_PER_GROUP ))
    END=$(( START + FILES_PER_GROUP - 1 ))
    if [ "$END" -ge "$TOTAL_FILES" ]; then
        END=$(( TOTAL_FILES - 1 ))
    fi

    # Write the VALIDATE file (files belonging to the current group)
    for ((j = START; j <= END; j++)); do
        echo "${SHUFFLED_ARRAY[$j]}" >> "$VALIDATE_FILE"
    done

    # Write the TRAIN  file (all files not in VALIDATE group 'i')
    for ((j = 0; j < START; j++)); do
        echo "${SHUFFLED_ARRAY[$j]}" >> "$TRAIN_FILE"
    done
    for ((j = END + 1; j < TOTAL_FILES; j++)); do
        echo "${SHUFFLED_ARRAY[$j]}" >> "$TRAIN_FILE"
    done
done

echo "K-fold train and validate files successfully created in $DATA_DIR."
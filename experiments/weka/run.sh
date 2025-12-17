#!/bin/sh

# Get the FOLD value. If not provided, it will be empty
FOLD=${1:-}

# If FOLD is empty, use a default file
if [[ -z "$FOLD" ]]; then
    DEFAULT_FILE="data/glass.arff"
    echo "FOLD was not specified. Using default file: $DEFAULT_FILE"


else
    # Verifica si el segundo parámetro es "-v"
    if [[ "$2" == "-v" ]]; then
      LIST_FILE="data/validate$FOLD"
    else
      LIST_FILE="data/train$FOLD"
    fi


    # Check if the file containing the relative paths exists
    if [ -f "$LIST_FILE" ]; then
        echo "Processing file paths from: $LIST_FILE"

        # Read each line from the file and execute the Java command
        while IFS= read -r relative_path; do
            if [ -f "$relative_path" ]; then
                echo "Executing for file: $relative_path"
                java -cp weka-src/build/classes/ weka.classifiers.trees.RandomForest -t "$relative_path"
            else
                echo "Warning: File $relative_path does not exist or is invalid."
            fi
        done < "$LIST_FILE"
    else
        echo "Error: File containing paths $LIST_FILE does not exist."
        exit 1
    fi
fi

exit 0
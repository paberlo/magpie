#!/bin/sh

# Get the FOLD value. If not provided, it will be empty
FOLD=${1:-}

# If FOLD is empty, use a default file
if [[ -z "$FOLD" ]]; then
    DEFAULT_FILE="data/logo.png"
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
                #-07 would b the highest optimization level. it means more iterations, but the reduced
                #time would probably keep the same.
               ./optipng-7.9.1/src/optipng/optipng "$relative_path" -o2 -out data/temp.png
                rm data/temp.png
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


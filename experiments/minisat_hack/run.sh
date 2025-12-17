#!/bin/sh

# Registrar una trampa para asegurarse de manejar señales y liberar recursos
trap clean_up EXIT SIGINT  # test_timeout error does not unlock executable file

clean_up() {
    # Finaliza cualquier proceso relacionado con el ejecutable en caso de error o interrupción
    pkill -f "./minisat_HACK_999ED_CSSC_static"
}


# Get the FOLD value. If not provided, it will be empty
FOLD=${1:-}

# If FOLD is empty, use a default file
if [[ -z "$FOLD" ]]; then
    DEFAULT_FILE="data/uf50-01.cnf"
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
               ./minisat_HACK_999ED_CSSC_static "$relative_path"
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
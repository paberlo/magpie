#!/bin/bash
#SBATCH --job-name=magpie_eda_array
#SBATCH --output=magpie_eda_%A_%a.out
#SBATCH --error=magpie_eda_%A_%a.err
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G

# Lista de carpetas de experimentos
DIRS=(sat4j minisat)
# Número de folds
FOLDS=5

# Comprobación básica
if [ -z "${SLURM_ARRAY_TASK_ID}" ]; then
  TOTAL=$(( ${#DIRS[@]} * FOLDS ))
  echo "SLURM_ARRAY_TASK_ID no definido. Enviar con:"
  echo "  TOTAL=${TOTAL}"
  echo "  sbatch --array=1-${TOTAL}%2 run_eda_array.slurm"
  exit 1
fi

task=${SLURM_ARRAY_TASK_ID}
n_dirs=${#DIRS[@]}

# Calcular indices (task comienza en 1)
fold=$(( (task - 1) % FOLDS + 1 ))
dir_index=$(( (task - 1) / FOLDS ))

if [ "${dir_index}" -ge "${n_dirs}" ]; then
  echo "Error: dir_index (${dir_index}) fuera de rango (n_dirs=${n_dirs})."
  exit 1
fi

dir=${DIRS[$dir_index]}

cd /home/pbermejo/GeneticImprovement/magpie

SCENARIO="experiments/${dir}/_magpie/scenario_runtime_xml_FOLD${fold}.txt"
echo "Ejecutando: ${SCENARIO}"
python3 magpie/__main__.py bin/eda --scenario "${SCENARIO}"

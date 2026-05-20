#!/bin/bash

REMOTE_USER="pbermejo"
REMOTE_HOST="galgo.uclm.es"
REMOTE_BASE="/home/pbermejo/GeneticImprovement/magpie"
LOCAL_BASE="/home/pablo/magpie"

rsync -avz "$REMOTE_USER@$REMOTE_HOST:$REMOTE_BASE/experiments/results/results.csv" "$LOCAL_BASE/experiments/results/results.csv"

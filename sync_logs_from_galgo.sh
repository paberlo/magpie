#!/bin/bash

REMOTE_USER="pbermejo"
REMOTE_HOST="galgo.uclm.es"
REMOTE_BASE="/home/pbermejo/GeneticImprovement/magpie"
LOCAL_BASE="/home/pablo/magpie"

rsync -avz "$REMOTE_USER@$REMOTE_HOST:$REMOTE_BASE/_magpie_logs/" "$LOCAL_BASE/_magpie_logs/"

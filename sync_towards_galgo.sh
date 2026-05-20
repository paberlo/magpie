#!/bin/bash

REMOTE_USER="pbermejo"
REMOTE_HOST="galgo.uclm.es"
REMOTE_BASE="/home/pbermejo/GeneticImprovement/magpie"
LOCAL_BASE="/home/pablo/magpie"

CTL="/tmp/galgo_ctl_$$"
SSH_OPTS="-o ControlMaster=auto -o ControlPath=$CTL -o ControlPersist=60"

rsync -avz -e "ssh $SSH_OPTS" "$LOCAL_BASE/magpie/"      "$REMOTE_USER@$REMOTE_HOST:$REMOTE_BASE/magpie/"
rsync -avz -e "ssh $SSH_OPTS" "$LOCAL_BASE/experiments/" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_BASE/experiments/"
rsync -avz -e "ssh $SSH_OPTS" "$LOCAL_BASE/galgo/"       "$REMOTE_USER@$REMOTE_HOST:$REMOTE_BASE/galgo/"

ssh -o ControlPath="$CTL" -O exit "$REMOTE_USER@$REMOTE_HOST" 2>/dev/null

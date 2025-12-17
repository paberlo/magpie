#!/usr/bin/env bash

#we compile upon the built version, only need to compile the target file
BUILD_FOLDER=weka-src/build/classes
FILE=weka-src/src/main/java/weka/classifiers/trees/RandomForest.java

javac -d $BUILD_FOLDER -cp $BUILD_FOLDER $FILE



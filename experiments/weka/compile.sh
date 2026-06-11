#!/usr/bin/env bash

#we compile upon the built version, only need to compile the target file
BUILD_FOLDER=weka-src/build/classes
FILE=RandomForest.java

# write_variant only writes $FILE when the patch actually changes the source;
# if absent, the prebuilt .class (original) is already correct
if [ ! -f "$FILE" ]; then
    exit 0
fi

javac -d $BUILD_FOLDER -cp $BUILD_FOLDER $FILE



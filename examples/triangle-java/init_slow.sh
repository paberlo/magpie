#!/usr/bin/env bash

patch Triangle.java _magpie/TriangleSlow.diff
#srcml Triangle.java > _magpie/TriangleSlow.java.xml
cp _magpie/TriangleSlow.java.xml Triangle.java.xml

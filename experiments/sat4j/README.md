[![Quality Gate Status](https://sonarqube.ow2.org/api/project_badges/measure?project=org.ow2.sat4j%3Aorg.ow2.sat4j.pom&metric=alert_status)](https://sonarqube.ow2.org/dashboard?id=org.ow2.sat4j%3Aorg.ow2.sat4j.pom)
[![pipeline status](https://gitlab.ow2.org/sat4j/sat4j/badges/master/pipeline.svg)](https://gitlab.ow2.org/sat4j/sat4j/commits/master)

# HOW TO DOWNLOAD SAT4J JAR FILES

- Older releases are available from [OW2 download repository](http://www.sat4j.org/ARCHIVE/) 
- Recent releases are available from [OW2 gitlab release page](https://gitlab.ow2.org/sat4j/sat4j/-/releases)
- Nighlty builds are available from [OW2 gitlab continuous integration](https://gitlab.ow2.org/sat4j/sat4j/pipelines)

# HOW TO BUILD SAT4J FROM SOURCE

## Using Maven (library users)

Just launch 

```shell
$ mvn -DskipTests=true install
```

to build the SAT4J modules from the source tree.

All the dependencies will be gathered by Maven.


## Using ant (solvers users)

Just type:

```shell
$ ant [core,pseudo,maxsat,sat]
```

to build the solvers from source.

The solvers will be available in the directory `dist/CUSTOM`.

You may want to use a custom release name.

```shell
$ ant -Drelease=MINE maxsat
```

In that case, the solvers will be available in the directory `dist/MINE`.

Type

```shell
$ ant -p
```

to see available options.

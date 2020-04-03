[![Licence](https://img.shields.io/badge/licence-Apache%202.0-green)]()
[![Helm](https://img.shields.io/badge/plugin-helm--unit--0.1.0-brightgreen)]()
[![Python](https://img.shields.io/badge/python-v3.7-green)]()

# helm-unit 

## Overview

`helm-unit` plugin provides you the ability to run unit-test on your helm chart templates locally without installing anything on your cluster.  

## Features
+ validate & render chart locally without creating anything on your cluster.
+ write unit test scenario in YAML file for every k8s object.
+ support umbrella chart

## Roadmap 
+ create `unit-test` directory to load automatically all unit-test files.
+ create a pre-check which evaluate all preconisations of k8s

## Prerequisite

+ Helm v3 installed on a your system
+ Access to k8s cluster


## Getting started 

### Installation

Install the latest version:

```
$ helm plugin install https://github.com/HamzaZo/helm-unit
```

Install a specific version:

```
$ helm plugin install https://github.com/HamzaZo/helm-unit --version 0.1.0-alpha
```

You can also verify it's been installed using:

```
$ helm plugin list
```

### Usage 

Running `helm unit`:
```
$ helm unit -h
usage: helm unit [CHART-DIR] [TEST-FILE]

The Helm TestUnit plugin runs tests on a chart locally without deloying the
release.

optional arguments:
  -h, --help   show this help message and exit
  --chart DIR  Specify chart directory
  --test FILE  Specify Test Unit in a YAML file
  --version    Print version information

```
+ Will render and validate locally `[CHART-DIR]`
+ Run tests defined in `[TEST-FILE]` YAML file on your`[CHART-DIR]`

### Examples 

While developing your helm chart, you want to validate and render your chart before deploy it on your CI/CD.

Example of test file for Deployment 
```yaml
tests:
  - description: Run the following test on deployment 
    type: Deployment
    name: nginx
    asserts:
    - name: check if we use the right number of replicas
      type: equal
      values:
      - path: spec.replicas
        value: 1 
    - name: check image tag
      type: notEqual
      values:
      - path: spec.template.spec.containers[0].image
        value: nginx:latest
    - name: check serviceAccount Name
      type: isNotEmpty
      values:
      - path: spec.template.spec.serviceAccountName
    - name: check container port value
      type: equal
      values:
      - path: spec.template.spec.containers[0].ports[0].containerPort
        value: 8080
    - name: verify if resource exist
      type: isNotEmpty
      values:
      - path: spec.template.spec.containers[0].resources
    - name: check that metadata labels are set and not empty
      type: isNotEmpty
      values:
      - path: metadata.labels

```

test file for Ingress 
```yaml
tests:
  - description: Run the following test on Ingress 
    type: Ingress
    name: demo-ing
    asserts:
    - name: check ingress path
      type: contains
      values:
      - path: spec.rules[*].http.paths[*].path
        value: /api
    - name: check that metadata labels are set and not empty
      type: isNotEmpty
      values:
      - path: metadata.labels
```

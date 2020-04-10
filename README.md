[![Licence](https://img.shields.io/badge/licence-Apache%202.0-green)]()
[![Helm](https://img.shields.io/badge/plugin-helm--unit--0.1.1-brightgreen)]()
[![Python](https://img.shields.io/badge/python-v3.7-green)]()

# helm-unit 

## Overview

Testing helm charts was always a challenge and the missing key word in the helm ecosystem, and that's where `helm-unit` comes in the place, it provides the ability to run unit-test on your helm chart templates locally without installing anything on your cluster.  

## Features
+ Validate & render chart locally without deploying **anything** on your cluster.
+ Write unit test scenario in **YAML** format.
+ Define all unit-test files in a directory.
+ Run and Load all unit-test files defined in a directory.


## Roadmap 
+ Create a pre-check which evaluates all preconisations of k8s.

## Prerequisite
+ Helm v3 installed on a your system
+ Access to k8s cluster


## Getting started 

### Installation

Install the latest version:

```shell
$ helm plugin install https://github.com/HamzaZo/helm-unit
```

Install a specific version:

```shell
$ helm plugin install https://github.com/HamzaZo/helm-unit --version 0.1.1
```

You can also verify it's been installed using:

```shell
$ helm plugin list
```

### Usage 

Running `helm unit`:

+ Will validate and render `[CHART-DIR]` locally.
+ Run all tests defined in `[TEST-DIR]` directory on `[CHART-DIR]`.
  
```shell
$ helm unit -h
usage: helm unit [CHART-DIR] [TEST-DIR]

Run unit-test on chart locally without deloying the release.

optional arguments:
  -h, --help    show this help message and exit
  --chart DIR   Specify chart directory
  --tests TESTS Specify Unit tests directory
  --version     Print version information

```


### Asserts types

`helm-unit` support the following asserts types :


| Assert | Params [Required] | type | Description | Example Usage  |
|----------------|----------------|---------|-------------|-------------|
| `equal` |<font color='#ff0055'>values</font> A set of values to validate<br/><font color='#1a75ff'>path</font> The path to assert<br/><font color='#1a75ff'>value</font> The expected value |map <br> string <br> string</font></pre>|Affirm the value of the specified **path** equal to the **value**.| <pre>type: equal <br/>values:<br/>- path: spec.replicas<br/>  value: 1</pre> |
| `notEqual` |<font color='#ff0055'>values</font> A set of values to validate <br/><font color='#1a75ff'>path</font> The path to assert<br/><font color='#1a75ff'>value</font> The expected value |map <br>string<br>string| Affirm the value of the specified **path** **NOT** equal to the **value**. | <pre>type: notEqual <br/>values:<br/>- path: spec.replicas<br/>  value: 1</pre> |
| `contains` |<font color='#ff0055'>values</font> A set of values to validate <br/><font color='#1a75ff'>path</font> The path to assert<br/><font color='#1a75ff'>value</font> The expected value |map<br>string<br>string| Asserting that the value of the specified **path** contains the content of the  **value**. | <pre>type: contains <br/>values:<br/>- path: metadata.labels<br/>  value: /api</pre> |
| `notContains` |<font color='#ff0055'>values</font> A set of values to validate <br/><font color='#1a75ff'>path</font> The path to assert<br/><font color='#1a75ff'>value</font> The expected value |map<br>string<br>string| Asserting that the value of the specified **path** does **NOT** contains the content of the  **value**. | <pre>type: notContains <br/>values:<br/>- path: metadata.labels<br/>  value:<br/>  - 'app.kubernetes.io/name: front' </pre> |
| `isEmpty` |<font color='#ff0055'>values</font> A set of values to validate. <br/><font color='#1a75ff'>path</font> The path to assert<br/> |map<br>string| Assert the value of the specified **path** is empty| <pre>type: isEmpty <br/>values:<br/>- path: metadata.labels</pre> |
| `isNotEmpty` |<font color='#ff0055'>values</font> A set of values to validate. <br/><font color='#1a75ff'>path</font> The path to assert<br/>|map<br>string| Assert the value of the specified **path** is **NOT** empty. | <pre>type: isNotEmpty <br/>values:<br/>- path: spec.template.spec</pre> |


### Example Use Case

Writing unit test files it's easy as writing a kubernetes manifest in YAML format. `helm-unit` can load and run a single unit-test file or a bunch of tests file placed in a specific directory by using `--tests` flags of cli.

We will use the [sample-front](example/sample-front/) chart as an example use case. We defined a several test scenario to run on frontend chart as follow:

Example of test file for Deployment 

```yaml
tests:
  - description: Run the following test on deployment 
    type: Deployment
    name: sample-front
    asserts:
    - name: check if we use the right number of replicas
      type: equal
      values:
      - path: spec.replicas
        value: 1 
    - name: check that container image does not using latest as tag
      type: notEqual
      values:
      - path: spec.template.spec.containers[0].image
        value: nginx:latest
    - name: validate that serviceAccount Name exist
      type: isNotEmpty
      values:
      - path: spec.template.spec.serviceAccountName
    - name: validate container port value
      type: equal
      values:
      - path: spec.template.spec.containers[0].ports[0].containerPort
        value: 80
    - name: ensure that cpu/memory resources were set 
      type: isNotEmpty
      values:
      - path: spec.template.spec.containers[0].resources
    - name: check that deployment metadata do not contains this labels
      type: notContains
      values:
      - path: metadata.labels
        value: "app.kubernetes.io/managed-by: Helm"
    - name: ensure that deployment does not have security context
      type: isEmpty
      values:
      - path: spec.template.spec.containers[0].securityContext

```

Example of test file for Ingress 

```yaml
tests:
  - description: Run the following test on Ingress 
    type: Ingress
    name: sample-front-ing
    asserts:
    - name: affirm that /api uri is exposed by ingress
      type: contains
      values:
      - path: spec.rules[*].http.paths[*].path
        value: /api
    - name: check that metadata labels are set and not empty
      type: isNotEmpty
      values:
      - path: metadata.labels
```

Example of test file for Service 

```yaml
tests:
  - description: Run the following test on service 
    type: Service
    name: sample-front-svc
    asserts:
    - name: check if service listen on the right port
      type: equal
      values:
      - path: spec.ports[0].port
        value: 80
    - name: ensure that service forward traffic to the right pod port
      type: equal
      values:
      - path: spec.ports[0].targetPort
        value: http
    - name: verify that service is using these labels as selector
      type: contains
      values:
      - path: metadata.labels
        value: 
        - "app.kubernetes.io/name: sample-front" 
        - "app.kubernetes.io/instance: tmp"
    - name: check if service is not exposed outside of the cluster
      type: equal
      values:
      - path: spec.type
        value: ClusterIP
```

Run test 

```shell
$ helm unit --chart example/sample-front --tests example/unit-test
✔️ Detecting Helm 3 : PASS 🎯

✔️ Validating chart syntax..⏳

==> Linting example/sample-front
PASS 🎯 

---> Applying test-service.yaml file..⏳

==> Running Tests on sample-front-svc Service ..

✔️ check if service listen on the right port : PASS 🎯

✔️ ensure that service forward traffic to the right pod port : PASS 🎯

✔️ verify that service is using these labels as selector app.kubernetes.io/name: sample-front: PASS 🎯

✔️ verify that service is using these labels as selector app.kubernetes.io/instance: tmp: PASS 🎯

✔️ check if service is not exposed outside of the cluster : PASS 🎯

---> Applying test-ingress.yaml file..⏳

==> Running Tests on sample-front-ing Ingress ..

✔️ affirm that /api uri is exposed by ingress : PASS 🎯

✔️ check that metadata labels are set and not empty : PASS 🎯

---> Applying test-deployment.yaml file..⏳

==> Running Tests on sample-front Deployment ..

✔️ check if we use the right number of replicas : PASS 🎯

✔️ check that container image does not using latest as tag : PASS 🎯

✔️ validate that serviceAccount Name exist : PASS 🎯

✔️ validate container port value : PASS 🎯

❌ ensure that cpu/memory resources were set : FAILED 

✔️ check that deployment metadata do not contains this labels : PASS 🎯

✔️ ensure that deployment does not have security context : PASS 🎯

==> Unit Tests Summary:

test-service.yaml  
Number of executed tests : 5
Number of success tests : 5
Number of failed tests : 0

test-ingress.yaml  
Number of executed tests : 2
Number of success tests : 2
Number of failed tests : 0

test-deployment.yaml  
Number of executed tests : 7
Number of success tests : 6
Number of failed tests : 1


🕸  Happy Helming testing day! 🕸

```


### Related project

The idea of asserts type was inspired by [helm-unittest](https://github.com/lrills/helm-unittest)


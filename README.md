# Spyderbat kubernetes deployment tools

This repository containers tooling to support the deployment and validation process of the spyderbat monitoring solution.

## cluster_collect.py - Spyderbat pre-deployment collection script.

In order to optimally configure and size the Spyderbat collection agent and backend to
support your kubernetes cluster, we have created a script that will collect some useful data and metrics
that Spyderbat can review to optimize the Helm installation or our agents, and size our backend appropriately.


### What does the script collect:
----------------------------
1. summary metrics about the nr of nodes, pods, deployments, replicasets, daemonsets, services and namespaces

    This helps us assess the size and load on your cluster

2. information about the nodes of the cluster, including their provisioned capacity and any taints applied to the nodes

    This helps us understand the headroom available in your cluster to add our agents, and helps us pro-actively recommend
    configuring tolerations on our agents to ensure visibility on all nodes

3. Cumulative metrics about what resource requests currently running pods are requesting (cpu, memory)

    This helps us understand the headroom available in your cluster to add our agents.

4. The name and namespaces of the deployments, daemonsets and services running on your cluster

    This helps us assess if any other daemonsets or deployments could interfere with our agents and helps us discover
    if your cluster has node-auto-scaling configured

5. PriorityClasses currently present for the cluster

    This helps us assess whether our agent will have sufficient priority to get scheduled on any new nodes being added
    to the cluster


### What this script does NOT collect:

We do not collect implementation and status details in the 'spec' and 'status' sections of the pods, deployments or daemonsets.
No sensitive data that might be present in these sections of the k8s resources (environment variables, configs) is collected.


### Requirements

This script should be run from a machine you currently use to manage your cluster from.

The following are required

1. python3.7 or higher
    https://www.python.org/downloads/

2. kubectl and a valid kube config file
    https://kubernetes.io/docs/tasks/tools/

    The script will call on the kubectl command to collect cluster information. The cluster(s) to install Spyderbat on
    should be one of the contexts configured in the kube config file.


### Usage
After installing the script run it as
```
./cluster_collect.py -h
    OR
python3 cluster_collect.py -h

for usage info
usage: cluster_collect.py [-h] [-k KUBECONFIG] [-c CONTEXT] [-o OUTPUT]

options:
  -h, --help            show this help message and exit
  -k KUBECONFIG, --kubeconfig KUBECONFIG
                        path to kubeconfig file (if omitted, default is ~/.kube/config)
  -c CONTEXT, --context CONTEXT
                        kubectl context to pull from (if none provided, all contexts in the kubectl config will be analyzed)
  -o OUTPUT, --output OUTPUT
                        output file (default is spyderbat-clusterinfo.json.gz)
```

By default, the script will collect information for all clusters configured in your kubeconfig file.
If you want to collect only for a single one, use the -c CONTEXT flag, with the name of the context
(as available in kubectl config get-contexts) to collect for.

For example:
```
./cluster_collect.py -c qacluster1
```
by default the output will go into a file called spyderbat-clusterinfo.json.gz
You can use the -o flag to use another filename.


### After collection
If the script ran successfully, please send the output file back to Spyderbat.
We will review the findings with you to discuss the next steps for your deployment.


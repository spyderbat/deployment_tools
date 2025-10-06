#!/usr/bin/env python3
import argparse
import gzip
import json
import subprocess
import sys
from collections import defaultdict

resource_types = ["namespaces", "nodes", "pods", "deployments", "replicasets", "daemonsets", "services", "priorityclasses"]

"""
A utility to collect non-sensitive sizing information about one or more
kubernetes clusters to optimize the Spyderbat deployment process of agents
on the cluster, and appropriately size the agents and Spyderbat backend.
"""

def summarize_cluster(index, index_schema):
    cluster_summary: dict[str, int] = {}
    cluster_summary['nr_nodes'] = len(index_schema['Node'])
    cluster_summary['nr_pods'] = len(index_schema['Pod'])
    cluster_summary['nr_deployments'] = len(index_schema['Deployment'])
    cluster_summary['nr_replicasets'] = len(index_schema['ReplicaSet'])
    cluster_summary['nr_daemonsets'] = len(index_schema['DaemonSet'])
    cluster_summary['nr_services'] = len(index_schema['Service'])
    cluster_summary['nr_namespaces'] = len(index_schema['Namespace'])
    return cluster_summary


def get_node_usage(index, index_schema):
    node_usage = defaultdict(dict)
    nodes = index_schema['Node'].values()
    pods = index_schema['Pod'].values()
    for node in nodes:
        provider = 'unknown'
        for label in node['metadata']['labels']:
            if "aws" in label or "amazon" in label:
                provider = "AWS EKS"
                break
            if "gke" in label or "google" in label:
                provider = "GCP GKE"
                break
            if "azure" in label:
                provider = "Azure AKS"
                break

        node_usage[node['metadata']['name']] = {
            "arch": node['status']['nodeInfo']['architecture'],
            "osImage": node['status']['nodeInfo']['osImage'],
            "containerRuntime": node['status']['nodeInfo']['containerRuntimeVersion'],
            "instance_type": node['metadata']['labels'].get('node.kubernetes.io/instance-type', "unknown"),
            "cores": int(node['status']['capacity']['cpu']),
            "capacity_pods": int(node['status']['capacity']['pods']),
            "usage_pods": 0,
            "headroom_pod": 0,
            "capacity_memory": convert_unit(node['status']['capacity']['memory']),
            "usage_memory": 0,
            "headroom_memory": 0,
            "capacity_cpu": convert_unit(node['status']['capacity']['cpu']),
            "usage_cpu": 0,
            "headroom_cpu": 0,
            "taints": node['spec'].get('taints', []),
            "control_plane": node['metadata']['labels'].get('node-role.kubernetes.io/controlplane', False),
            "provider": provider
        }

    for pod in pods:
        node_name = pod['spec'].get('nodeName')
        if node_name:
            node_usage[node_name]['usage_pods'] += 1
            for container in pod['spec']['containers']:
                if 'resources' not in container:
                    continue
                if 'requests' not in container['resources']:
                    continue
                node_usage[node_name]['usage_memory'] += convert_unit(container['resources']['requests'].get('memory',0))
                node_usage[node_name]['usage_cpu'] += convert_unit(container['resources']['requests'].get('cpu',0))
    return node_usage


def convert_unit(amount):
    if type(amount) == int:
        return amount
    stripped = amount.strip()
    if stripped.endswith('m'):
        return int(stripped[:-1])/1000
    stripped = stripped.upper()
    if stripped.endswith('KI'):
        return int(stripped[:-2])*1024
    if stripped.endswith('MI'):
        return int(stripped[:-2])*1024*1024
    if stripped.endswith('GI'):
        return int(stripped[:-2])*1024*1024*1024
    if stripped.endswith('TI'):
        return int(stripped[:-2])*1024*1024*1024*1024
    if stripped.endswith('PI'):
        return int(stripped[:-2])*1024*1024*1024*1024*1024
    if stripped.endswith('EI'):
        return int(stripped[:-2])*1024*1024*1024*1024*1024*1024
    if stripped.endswith('K'):
        return int(stripped[:-1])*1000
    if stripped.endswith('M'):
        return int(stripped[:-1])*1000*1000
    if stripped.endswith('G'):
        return int(stripped[:-1])*1000*1000*1000
    if stripped.endswith('T'):
        return int(stripped[:-1])*1000*1000*1000*1000
    if stripped.endswith('P'):
        return int(stripped[:-1])*1000*1000*1000*1000*1000
    if stripped.endswith('E'):
        return int(stripped[:-1])*1000*1000*1000*1000*1000*1000
    return float(stripped)


def condense_resources(cluster_data, kind):
    resources = cluster_data['index_schema'].get(kind, {})
    return [{"name": r['metadata']['name'],
             "namespace": r['metadata']['namespace'],
             "uid": r['metadata']['uid']
            } for r in resources.values()]


def condense(cluster_index):
    rv = {}
    for cluster_name, cluster_data  in cluster_index.items():
        cluster_summary = summarize_cluster(cluster_data['index'], cluster_data['index_schema'])
        node_usage = get_node_usage(cluster_data['index'], cluster_data['index_schema'])
        deployments = condense_resources(cluster_data, 'Deployment')
        daemonsets = condense_resources(cluster_data, 'DaemonSet')
        services = condense_resources(cluster_data, 'Service')
        pods = condense_resources(cluster_data, 'Pod')

        # deps = cluster_data['index_schema'].get('Deployment', {})
        # deployments = [{"name": dep['metadata']['name'], "namespace": dep['metadata']['namespace'], "replicas": dep['spec']['replicas']} for dep in deps.values()]
        # daems = cluster_data['index_schema'].get('DaemonSet', {})
        # daemonsets = [{"name": d['metadata']['name'], "namespace": d['metadata']['namespace'], } for d in daems.values()]
        # svcs = cluster_data['index_schema'].get('Service', {})
        # services = [{"name": d['metadata']['name'], "namespace": d['metadata']['namespace'] } for d in svcs.values()]
        # pods = cluster_data['index_schema'].get('Pod', {})
        # services = [{"name": r['metadata']['name'], "namespace": r['metadata']['namespace'], "uid": r['metadata']['uid'] } for r in pods.values()]

        rv[cluster_name] = {
            "cluster_summary": cluster_summary,
            "node_usage": node_usage,
            "deployments": deployments,
            "daemonsets": daemonsets,
            "services": services,
            "pods": pods,
            "nodes": cluster_data['index_schema'].get('Node', {}),
            "priority_classes": cluster_data['index_schema'].get('PriorityClass', {})
        }
    return rv


def load(args):
    kubeconfig = f"--kubeconfig {args.kubeconfig}" if args.kubeconfig else ""

    if args.context is None:
        cmd = f"kubectl {kubeconfig} config get-contexts -o name"
        contexts = subprocess.check_output(cmd, shell=True).decode('utf-8').split('\n')[:-1]
    else:
        contexts = [args.context]

    cluster_index = defaultdict(dict)

    for context in contexts:
        print(f'collecting data for {context}...', file=sys.stderr)
        index_schema = defaultdict(dict)
        index = {}

        for resource_type in resource_types:
            cmd = f"kubectl {kubeconfig} --context {context} get {resource_type} -A -o json"
            try:
                result = subprocess.check_output(cmd, shell=True)
                resources = json.loads(result)
                for res in resources['items']:
                    uid = res['metadata']['uid']
                    index_schema[res['kind']][uid] = res
                    index[uid] = res
            except subprocess.CalledProcessError:
                print(f'failed to get {resource_type} from {context}, skipping')
                pass
        if len(index) != 0:
            cluster_index[context]['index'] = index
            cluster_index[context]['index_schema'] = index_schema
    return cluster_index


def parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("-k", "--kubeconfig",
                        help="path to kubeconfig file (if omitted, default is ~/.kube/config)")
    parser.add_argument("-c", "--context",
                        help="kubectl context to pull from (if none provided, all contexts in the kubectl config will be analyzed)",
                        required=False)
    parser.add_argument("-o", "--output",
                        help="output file (default is spyderbat-clusterinfo.json.gz)",
                        default = "spyderbat-clusterinfo.json.gz")

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    cluster_index = load(args)
    cluster_condensed = condense(cluster_index)
    with gzip.open(args.output, 'wt') as f:
        json.dump(cluster_condensed, f)
        print('Done. Output written to', args.output, file=sys.stderr)

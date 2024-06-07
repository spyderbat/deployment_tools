#!/usr/bin/env python3
from __future__ import annotations
import argparse
import gzip
import json
import sys
from collections import defaultdict

import termtables
import yaml

import toollib as tlib
import cluster_collect

s_cluster     = "model_k8s_cluster::1.0.0"
s_node        = "model_k8s_node::1.0.0"
s_replicaset  = "model_k8s_replicaset::1.0.0"
s_daemonset   = "model_k8s_daemonset::1.0.0"
s_deployment  = "model_k8s_deployment::1.0.0"
s_pod         = "model_k8s_pod::1.0.0"
s_service     = "model_k8s_service::1.0.0"
s_endpoint    = "model_k8s_endpoint::1.0.0"
s_statefulset = "model_k8s_statefulset::1.0.0"
s_job         = "model_k8s_job::1.0.0"
s_cronjob     = "model_k8s_cronjob::1.0.0"
s_container   = "model_container::1.0.0"

k8s_schemas = [s_cluster, s_node, s_replicaset, s_daemonset, s_deployment, s_pod, s_service]


def report_clusters(cluster_analyzed: dict, args: argparse.Namespace) -> str:

    if args.format == 'text':
        rv = ""
        for cluster, analysis in cluster_analyzed.items():
            if args.cluster != 'all' and args.cluster != cluster:
                continue
            rv += "\n───────────────────" + "─"*len(cluster) + "\n"
            rv += f"Cluster report for {cluster}\n"
            rv += "───────────────────" + "─"*len(cluster) + "\n\n"
            rv += "Cluster summary metrics\n"
            rv += render_metrics(analysis['cluster_summary'])
            rv += "\n\n"
            node_usage = analysis['node_usage']
            nr_nodes =len(node_usage)
            if nr_nodes > 0:
                rv += "Node information\n"
                info_fields = ['arch', 'osImage', 'containerRuntime', 'instance_type', 'provider', 'control_plane']
                header = ["Node"] + info_fields
                rows = []
                for node_name, node in node_usage.items():
                    row = [node_name]
                    row.extend([str(node[f]) for f in info_fields])
                    rows.append(row)
                rv += termtables.to_string(data=rows, header=header, style=termtables.styles.rounded_double)

                rv += "\n\nNode usage\n"
                capacity_fields = ['instance_type',
                                   'cores',
                                   'capacity_pods',
                                   'capacity_cpu',
                                   'capacity_memory',
                                   'usage_pods',
                                   'usage_cpu',
                                   'usage_memory',
                                   'headroom_pod',
                                   'headroom_cpu',
                                   'headroom_memory',
                                   'taints']
                header = ["Node"] + capacity_fields
                rows = []
                for node_name, node in sorted(node_usage.items(),
                                              key=lambda x: (x[1]['cores'],
                                                             x[1]['capacity_pods'],
                                                             x[1]['capacity_cpu'],
                                                             x[1]['capacity_memory']),
                                              reverse=True):
                    row = [node_name]
                    row.extend([node['instance_type'],
                                node['cores'],
                                node['capacity_pods'],
                                node['capacity_cpu'],
                                f"{node['capacity_memory']/1024/1024:0.2f} MB",
                                node['usage_pods'],
                                f"{node['usage_cpu']:0.2f}",
                                f"{node['usage_memory']/1024/1024:0.2f} MB",
                                node['headroom_pod'],
                                f"{node['headroom_cpu']:0.2f}",
                                f"{node['headroom_memory']/1024/1024:0.2f} MB",
                                str([n['key'] for n in node['taints']])
                    ])
                    rows.append(row)
                rv += termtables.to_string(data=rows, header=header, style=termtables.styles.rounded_double)

            services = analysis['services']
            if len(services) > 0:
                rv += "\n\nServices\n"
                header = ["Namespace", "Name"]
                rows = [[d['namespace'], d['name']] for d in sorted(services, key=lambda x: (x['namespace'], x['name']))]
                rv += termtables.to_string(data=rows, header=header, style=termtables.styles.rounded_double)

            deployments = analysis['deployments']
            if len(deployments) > 0:
                rv += "\n\nDeployments\n"
                header = ["Namespace", "Name", "Replicas"]
                rows = [[d['namespace'], d['name'], d.get("replicas", "")] for d in sorted(deployments, key=lambda x: (x['namespace'], x['name']))]
                rv += termtables.to_string(data=rows, header=header, style=termtables.styles.rounded_double)

            daemonsets = analysis['daemonsets']
            if len(daemonsets) > 0:
                rv += "\n\nDaemonsets\n"
                header = ["Namespace", "Name"]
                rows = [[d['namespace'], d['name']] for d in sorted(daemonsets, key=lambda x: (x['namespace'], x['name']))]
                rv += termtables.to_string(data=rows, header=header, style=termtables.styles.rounded_double)

            priority_classes = analysis['priority_classes']
            if len(priority_classes) > 0:
                rv += "\n\nPriorityClasses\n"
                header = ["Name", "Value", "PreemptionPolicy"]
                rows = [[d['metadata']['name'],
                        d['value'],
                        d['preemptionPolicy']] for d in analysis['priority_classes'].values()]
                rv += termtables.to_string(data=rows, header=header, style=termtables.styles.rounded_double)

            warnings = analysis['warnings']
            if len(warnings) == 0:
                rv += "\n\nThere are no warnings\n"
            else:
                rv += "\n\nWarnings\n"
                header = ["Resource", "Warning", "Detail"]
                rows = [[w['resource'], w['warning'], w['detail']] for w in sorted(warnings, key=lambda x:x['warning'])]
                rv += termtables.to_string(data=rows, header=header, style=termtables.styles.rounded_double)
        return rv

    else:
        return json.dumps(cluster_analyzed)


def analyze(clusters_condensed: dict) -> dict:

    for cluster in clusters_condensed.values():
        warnings = []

        for svc in cluster['services']:
            if 'cluster-autoscaler' in svc['name']:
                warnings.append({"resource": "cluster-wide",
                                    "warning": "cluster-autoscaler detected. Ensure spyderbat agents have high enough priority class to scale out cluster if needed",
                                    "detail": f"service: {svc['name']}, namespace: {svc['namespace']}"})

        warnings += node_warnings(cluster['node_usage'])
        cluster['warnings'] = warnings
    return clusters_condensed


def node_warnings(node_usage: dict) -> list[dict]:
    warnings = []
    for node_name, node in node_usage.items():
        if node['taints']!=[]:
            warnings.append({"resource": f"Node {node_name}",
                            "warning": "node has taints, make sure the nano-agent tolerates them",
                            "detail":  f"taints: {node['taints']}"})

        node['headroom_pod'] = headroom = node['capacity_pods'] - node['usage_pods']
        if headroom <= 2:
            warnings.append({"resource": f"Node {node_name}",
                            "warning": f"pod capacity warning: node pod headroom is only {headroom:0.2f} pods, ensure nano-agent/cluster monitor can be scheduled",
                            "detail":  f"pod capacity headroom: {headroom:0.2f}"})
        node['headroom_cpu'] = headroom = node['capacity_cpu'] - node['usage_cpu']
        if headroom < 0.2:
            warnings.append({"resource": f"Node {node_name}",
                            "warning": f"cpu capacity warning: node cpu headroom is only {headroom:0.2f} CPU, ensure nano-agent can be scheduled",
                            "detail":  f"cpu headroom: {headroom:0.2f}"})
        node['headroom_memory'] = headroom = node['capacity_memory'] - node['usage_memory']
        if headroom < 512*1024*1024:
            warnings.append({"resource": f"Node {node_name}",
                            "warning": f"memory capacity warning: node memory headroom is only {headroom/1024/1024:0.2f} MB, ensure nano-agent can be scheduled",
                            "detail":  f"memory headroom: {headroom/1024/1024:0.2f}"})

    for metric in ['capacity_pods', 'capacity_cpu', 'capacity_memory']:
        capacity = [(name, int(node[metric])) for name, node in node_usage.items()]
        maxcap = max([c[1] for c in capacity])
        wnodes = [node for node in capacity if node[1] < 0.5*maxcap]
        if len(wnodes) > 0:
            warnings.append({"resource": "See nodes capacity overview",
                            "warning": "some nodes much smaller then others, consider using differentiated daemonset sizing",
                            "detail":  "See nodes capacity overview"})
            break
    return warnings


def render_metrics(metrics: dict) -> str:
    header = ["Metric", "Value"]
    rows = [[k,v] for k,v  in metrics.items()]
    return termtables.to_string(data=rows, header=header, style=termtables.styles.rounded_double)

def from_model(index: dict) -> dict:
    cluster_index = defaultdict(dict)
    for model in index.values():
        if 'cluster' in model['schema']:
            clustername = model['name']
            clusterid = model['id']
            namespaces = model['namespaces']
            cluster_index[clusterid].setdefault("index_schema", {})
            cluster_index[clusterid]['index_schema'].setdefault("Namespace", {})
            for i, ns in enumerate(namespaces):
                cluster_index[clusterid]['index_schema']["Namespace"][i] = ns

        else:
            cluster = model.get("cluster_uid", "unknown")
            uid = model['metadata']['uid']
            kind = model['kind']
            if 'k8s_status' in model:
                model['spy_status'] = model['status']
                model['status'] = model['k8s_status']
            cluster_index[cluster].setdefault("index_schema", {})
            cluster_index[cluster]['index_schema'].setdefault(kind, {})
            cluster_index[cluster]['index_schema'][kind][uid] = model
            cluster_index[cluster].setdefault("index", {})
            cluster_index[cluster]['index'][uid] = model
    for cluster in cluster_index.values():
        cluster['priority_classes'] = []
    return cluster_index


def parse_args(args: list) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input",
                        help="input file (default is spyderbat-clusterinfo.json.gz)",
                        default="spyderbat-clusterinfo.json.gz",
                        required=True)
    parser.add_argument("-t", "--type_input",
                        help="type of input: kubectl output, or analytic model output",
                        default="kubectl",
                        choices=['kubectl', 'model'])
    parser.add_argument("-f", "--format",
                        help="output format (default text)",
                        default="text",
                        choices=['text', 'json'])
    parser.add_argument("-c", "--cluster",
                        help="cluster name to report on (default all)",
                        default="all",
                        required=False)
    parser.add_argument("--helm-values",
                        help="create helm values file for cluster helm customization",
                        action="store_true")

    return parser.parse_args()


def create_helm_values(clusters_condensed: dict):
    for cluster_name, cluster in clusters_analyzed.items():
        node_usage = cluster['node_usage']
        taints = {}
        for node_name, node in node_usage.items():
            for taint in node['taints']:
                key = taint['key']
                value = taint.get("value")
                taints[(key, value)] = taint

        if len(taints) > 0:
            nanoagent = {"nanoagent": {"tolerations": list(taints.values())}}
            with open(f'{cluster_name}.values.yaml', 'w') as f:
                yaml.dump(nanoagent, f)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    with tlib.smart_open(args.input, 'rt') as f:
        if (args.type_input == 'kubectl'):
                clusters_condensed = json.load(f)
        if (args.type_input == 'model'):
            index = tlib.last_model(
                rec_list=f,
                schemas=k8s_schemas,
                extra_index_by=[]
            )
            cluster_index = from_model(index["id"])
            clusters_condensed = cluster_collect.condense(cluster_index)

        clusters_analyzed = analyze(clusters_condensed)
        print(report_clusters(clusters_analyzed, args))
        if (args.helm_values):
            create_helm_values(clusters_condensed)

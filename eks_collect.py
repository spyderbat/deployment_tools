import argparse
import sys
import boto3
import json

def get_nodegroup_info(region):
    eks = boto3.client('eks', region_name = region)
    info=[]
    cluster_response = eks.list_clusters()
    status_code = cluster_response['ResponseMetadata']['HTTPStatusCode']
    if status_code != 200:
        print(f'Got response code {status_code} calling list_clusters api')
        return [{"error": cluster_response}]
    clusters = cluster_response.get("clusters", [])
    for cluster in clusters:
        nodegroups_response = eks.list_nodegroups(clusterName = cluster)
        status_code = nodegroups_response['ResponseMetadata']['HTTPStatusCode']
        if status_code != 200:
            print(f'Got response code {status_code} calling list_nodegroups api for {cluster}')
            info.append({"cluster": cluster, "error": nodegroups_response})
            continue
        nodegroups = nodegroups_response.get("nodegroups", [])
        for group in nodegroups:
            groupinfo = eks.describe_nodegroup(clusterName=cluster, nodegroupName=group)
            if status_code != 200:
                print(f'Got response code {status_code} calling describe_nodegroup api for {cluster}/{group}')
                info.append({"cluster": cluster, "nodegroup": group, "error": groupinfo})
            else:
                del groupinfo['ResponseMetadata']
                info.append({"cluster": cluster, "nodegroup": group, "info": groupinfo})
    return info

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Get EKS nodegroup info')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('-o', '--output', default='stdout', help='Output file')
    args = parser.parse_args()
    info = get_nodegroup_info(args.region), open(args.output, 'w')
    output = sys.stdout if args.output == 'stdout' else open(args.output, 'w')
    json.dump(get_nodegroup_info(args.region), output, default=str)

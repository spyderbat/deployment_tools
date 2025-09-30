#!/usr/bin/env python3
import sys
import json

def process_item(item, filename):
    print(filename)
    for data in item.values():
        cluster_summary = data['cluster_summary']
        node_usage = data['node_usage']

        archs = set()
        total_cores = 0
        total_core_usage = 0
        for hostname, node_info in node_usage.items():
            archs.add(node_info["arch"])
            total_cores += node_info["cores"]
            scaling_factor = node_info["cores"] / node_info["capacity_cpu"]
            total_core_usage += node_info["usage_cpu"] * scaling_factor
        print ("  Architectures: ", ", ".join(archs))
        print ("  Number of nodes: ", cluster_summary['nr_nodes'])
        print ("  Number of cores: ", total_cores)
        min_cores = total_cores*0.02
        max_cores = total_cores*0.04
        core_headroom = total_cores-total_core_usage
        print (f"  Cores required: {min_cores:1.2f} - {max_cores:1.2f}") 
        print (f"  Core headroom: {core_headroom:1.2f}")
        util = 1.0 - (core_headroom/total_cores)
        print (f"  Core utilization: {(100.0*util):1.1f}%")
        print ("")



def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <file1.json> [file2.json ...]")
        sys.exit(1)

    for filename in sys.argv[1:]:
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)

                process_item(data, filename)

        except FileNotFoundError:
            print(f"Error: File not found: {filename}", file=sys.stderr)
        except json.JSONDecodeError as e:
            print(f"Error: Could not parse JSON in {filename}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()



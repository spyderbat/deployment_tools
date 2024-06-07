import subprocess
import time
import json
import yaml
import re


def cpu_parser(input):
    milli_match = re.match(r"^([0-9]+)m$", input)
    if milli_match:
        return int(milli_match.group(1)) / 1000
    return float(input)


memory_multipliers = {
    "k": 1000,
    "M": 1000**2,
    "G": 1000**3,
    "T": 1000**4,
    "P": 1000**5,
    "E": 1000**6,
    "Ki": 1024,
    "Mi": 1024**2,
    "Gi": 1024**3,
    "Ti": 1024**4,
    "Pi": 1024**5,
    "Ei": 1024**6,
}


def memory_parser(input):
    unit_match = re.match(r"^([0-9]+)([A-Za-z]{1,2})$", input)
    if unit_match:
        return int(unit_match.group(1)) * memory_multipliers[unit_match.group(2)]
    return int(input)


# subprocess.run(["python", "cluster_collect.py"])
# subprocess.run(
#    [
#        "python",
#        "cluster_analyze.py",
#        "-i",
#        "spyderbat-clusterinfo.json.gz",
#        "-t",
#        "kubectl",
#        "--helm-values",
#    ]
# )
# subprocess.run(
#    ["cat", "current-context.values.yaml"],
# )
# print("not blocked")
# subprocess.run(["kubectl-nodepools", "list", "--no-headers"])
# print("blocked")
# Define the commands
command1 = ["kubectl", "get", "nodes", "-o", "json"]
command2 = [
    "jq",
    '.items | .[] | {"cpu": .status.allocatable.cpu,"memory":.status.allocatable.memory,"type":.metadata.labels."beta.kubernetes.io/instance-type"}',
]
command3 = ["jq", "-s", "."]

# Create the pipelines
p1 = subprocess.Popen(command1, stdout=subprocess.PIPE)
print(p1)
p2 = subprocess.Popen(command2, stdin=p1.stdout, stdout=subprocess.PIPE)
print(p2)
p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
p3 = subprocess.Popen(command3, stdin=p2.stdout, stdout=subprocess.PIPE)
print(p3)
p2.stdout.close()  # Allow p2 to receive a SIGPIPE if p3 exits.

# Execute the pipeline
output = p3.communicate()[0]
print(output)
# Load the JSON output
foo = json.loads(output)

a = {}
for i in foo:
    a[i["type"]] = {
        "cpu": cpu_parser(i["cpu"]) * 0.04,
        "memory": memory_parser(i["memory"]) * 0.04,
    }
print(yaml.dump(a))
time.sleep(1000000)

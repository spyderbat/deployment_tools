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


print("# Paste the following lines into your values.yaml file")
# subprocess.run(["kubectl-nodepools", "list", "--no-headers"])
# Define the commands
command1 = """kubectl get pods -A -o json | jq '.items | .[] | {"priorityClassName": .spec.priorityClassName , "priority": .spec.priority }' | jq -s . """
command1o = subprocess.run(command1, shell=True, capture_output=True, text=True)
data = json.loads(command1o.stdout)
sc = {}
for i in data:
    if i["priority"] is not None and i["priority"] != 0:
        if i["priorityClassName"] not in sc:
            sc[i["priorityClassName"]] = i["priority"]

highValue = 0
highName = ""
for i, v in sc.items():
    if v > highValue:
        highValue = v
        highName = i

output = {
    "priorityClassDefault": {"enabled": True, "name": highName, "value": highValue}
}
print(
    "# this sets our priority class to the highest priority class in the cluster -- WARNING: this may not be what you want"
)
print(yaml.dump(output))

command1 = ["kubectl", "get", "nodes", "-o", "json"]
command2 = [
    "jq",
    '.items | .[] | {"cpu": .status.allocatable.cpu,"memory":.status.allocatable.memory,"type":.metadata.labels."beta.kubernetes.io/instance-type"}',
]
command3 = ["jq", "-s", "."]

command = """kubectl get nodes -o json | jq '.items | .[] | {"cpu": .status.allocatable.cpu,"memory":.status.allocatable.memory,"type":.metadata.labels."beta.kubernetes.io/instance-type"}' | jq -s ."""
result = subprocess.run(command, shell=True, capture_output=True, text=True)

# Parse the output as JSON
foo = json.loads(result.stdout)

a = {}
for i in foo:
    a[i["type"]] = {
        "cpu": cpu_parser(i["cpu"]) * 0.04,
        "memory": memory_parser(i["memory"]) * 0.04,
    }
output = {"collector": a}
print(yaml.dump(output))
time.sleep(1000000)

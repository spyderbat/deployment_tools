import os
import json

def main():
    # run kubectl cli on nodes tool and capture outu as json
    os.system("kubectl get nodes -o json > nodes.json")
    # read json file
    with open("nodes.json") as f:
        # find the allocatable cpu in memory in the json file
        # .items | .[] | .status.allocatable.cpu
        # .items | .[] | .status.allocatable.memory
        foo = json.load(f)
        print(json)
        for item in foo['items']:
            print(item['status']['allocatable']['cpu'])
            print(item['status']['allocatable']['memory'])


if __name__ == "__main__":
    main()

import json
import yaml
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser("Bump the version of turbonomic in the turbo-config configmap for Turbo 7")

    parser.add_argument('jsonfile', help="The full path to a json file in the format of the turbo-config configmap")
    parser.add_argument('version', help="The desired version")
    parser.add_argument('--hanodeconfig', help="A comma separated list of node roles for HANodeConfig")

    args = parser.parse_args()

    with open(args.jsonfile, 'r') as f:
        obj = json.load(f)

    obj['communicationConfig']['serverMeta']['version'] = args.version
    if args.hanodeconfig:
        obj['HANodeConfig']['nodeRoles'] = args.hanodeconfig.split(',')

    with open(args.jsonfile, 'w') as f:
        f.write(json.dumps(obj, indent=4))

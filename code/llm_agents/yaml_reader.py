from pathlib import Path
import yaml

def read(yaml_path):
    with open(Path(yaml_path), 'r', encoding='utf-8') as open_yml:
        yaml_file = yaml.safe_load(open_yml)
    return yaml_file


def get_all_titles(d, current_list):  # Function to collect all the titles from the yaml recursively 
    for k, v in d.items():
        if isinstance(v, dict):
            get_all_titles(v, current_list)
        else:
            current_list.append(v.replace('\\',''))
    return current_list


def rollout_dict(d, full_dict):    # Function to get the leaves of the hierarchy of titles as a dictionary
    for k, v in d.items():
        if isinstance(v, dict):
            rollout_dict(v, full_dict)
        else:
            full_dict[k] = v
    return full_dict
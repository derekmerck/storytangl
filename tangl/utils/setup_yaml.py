from uuid import UUID

import yaml

def uuid_representer(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data.hex)

def uuid_constructor(loader, node):
    value = loader.construct_scalar(node)
    try:
        return UUID(value)
    except ValueError as e:
        return value

yaml.add_representer(UUID, uuid_representer)
yaml.add_constructor('tag:yaml.org,2002:str', uuid_constructor)

def string_representer(dumper, data):
    if "\n" in data or len(data) > 150:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

yaml.add_representer(str, string_representer)

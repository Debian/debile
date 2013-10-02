import yaml

ROOT = "/etc/debile"


def import_from_yaml(whence):
    return yaml.safe_load(open(whence, 'r'))


def load_master_config():
    return import_from_yaml("{root}/master.yaml".format(root=ROOT))


def load_slave_config():
    return import_from_yaml("{root}/slave.yaml".format(root=ROOT))

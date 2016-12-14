from flask import Flask
from configparser import ConfigParser
from sys import stderr

from ..ldrresolverapi.api import BP

def retrieve_resource_string(resource_path, pkg_name=None):
    """
    retrieves the string contents of some package resource
    __Args__
    1. resource_path (str): The path to the resource in the package
    __KWArgs__
    * pkg_name (str): The name of a package. Defaults to the project name
    __Returns__
    * (str): the resource contents
    """
    from pkg_resources import Requirement, resource_string
    if pkg_name is None:
        pkg_name = __name__.split('.')[0]
    return resource_string(Requirement.parse(pkg_name), resource_path)

app = Flask(__name__)

config_str = retrieve_resource_string("config/config.ini").decode("utf-8")
parser = ConfigParser()
parser.read_string(config_str)

for x in parser["CONFIG"]:
    v = parser["CONFIG"][x]
    if v == "True":
        v = True
    if v == "False":
        v = False
    if x.upper() == "VALID_KEYS":
        app.config[x.upper()] = v.split(',')
    else:
        app.config[x.upper()] = v

app.register_blueprint(BP)

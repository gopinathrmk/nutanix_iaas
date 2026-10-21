import os
import json
from calm.dsl.builtins import *
from calm.dsl.builtins import (
    GlobalVariable,
    CalmVariable,
    Ref,
    ref,
    Metadata,
    CalmTask as CalmVarTask,
)
from calm.dsl.runbooks import RunbookTask as CalmTask

base_folder = "./"
env_file = base_folder + "config/environment.txt"
env_data = {}

# Load Environment Data
try:
    with open(env_file, "r") as f:
        content = f.read()
        if content:
            env_data = json.loads(content)
        else:
            print("Environment data not found!!")
            exit(1)
except Exception as e:
    print(f"File Open Failed : {env_file} \n Unexpected error: {e}")
    exit(1)



NC_FQDN = GlobalVariable(
    definition=CalmVariable.Simple(env_data["NCM"]["fqdn"], label="", description=""),
    projects=[],
)

# PC_details = GlobalVariable(
#     definition=CalmVariable.Simple(json.dumps(env_data["PC_details"]), label="", description=""),
#     projects=[],
# )

class GlobalVariableMetadata(Metadata):
    project = Ref.Project(env_data["NCM"]["project"])

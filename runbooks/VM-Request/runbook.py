
import os
import json
from calm.dsl.runbooks import *
from calm.dsl.runbooks import (
    CalmEndpoint as Endpoint,
    RunbookTask as CalmTask,
    RunbookVariable as CalmVariable,
)
from calm.dsl.builtins import CalmTask as CalmVarTask, Metadata

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

BP_CRED_API_CRED = dynamic_cred(
    "@@{username}@@",
    Ref.Account(env_data["NCM"]["cred_provider"]),
    resource_type=Ref.Resource_Type(env_data["NCM"]["cred_provider"]),
    variable_dict={
        "type": "api",
    },
    name="API_CRED",
    default=True,
    type="PASSWORD",
)

# print(env_data)

# Runbook
@runbook
def VM_Request(credentials=[BP_CRED_API_CRED]):

    # bp_name = CalmVariable.Simple(
    #     env_data["NCM"]["bp1_name"], label="", is_mandatory=False, is_hidden=False, runtime=False, description=""
    # )  
    NC_FQDN = CalmVariable.Simple(
        env_data["NCM"]["fqdn"], label="", is_mandatory=False, is_hidden=False, runtime=False, description=""
    )  
    PC_details = CalmVariable.Simple(
        json.dumps(env_data["PC_details"]), label="", is_mandatory=False, is_hidden=False, runtime=False, description=""
    )
    #global_variables = [Ref.GlobalVariable("PC_details")]
    #global_variables = [Ref.GlobalVariable("NC_FQDN")]

    # App Details 
    app_type = CalmVariable.Simple(
        "", label="", is_mandatory=False, is_hidden=False, runtime=True, description=""
    )  
    env = CalmVariable.Simple(
        "", label="", is_mandatory=False, is_hidden=False, runtime=True, description=""
    )  
    site = CalmVariable.Simple(
        "", label="", is_mandatory=False, is_hidden=False, runtime=True, description=""
    )  

    # VM Details
    tshirt = CalmVariable.Simple(
        "", label="", is_mandatory=False, is_hidden=False, runtime=True, description=""
    )  
    vcpu = CalmVariable.Simple.int(
        "",
        label="",
        regex="^[\\d]*$",
        validate_regex=False,
        is_mandatory=False,
        is_hidden=False,
        runtime=True,
        description="",
    )  
    ram = CalmVariable.Simple.int(
        "",
        label="",
        regex="^[\\d]*$",
        validate_regex=False,
        is_mandatory=False,
        is_hidden=False,
        runtime=True,
        description="",
    )  
    os_name = CalmVariable.Simple(
        "", label="", is_mandatory=False, is_hidden=False, runtime=True, description=""
    )  

    lin_version = CalmVariable.Simple(
        "", label="", is_mandatory=False, is_hidden=False, runtime=True, description=""
    )  

    win_version = CalmVariable.Simple(
        "", label="", is_mandatory=False, is_hidden=False, runtime=True, description=""
    )  

    # Infra Details
    infra_selection = CalmVariable.Simple(
        "", label="", is_mandatory=False, is_hidden=False, runtime=True, description=""
    )  
    pc_name = CalmVariable.WithOptions.FromTask(
        CalmVarTask.Exec.escript.py3(
            name="",
            filename=os.path.join(
                "scripts", "pc_dropdown.py"
            ),
        ),
        label="",
        is_mandatory=False,
        is_hidden=False,
        description="",
    )  
    cluster_name = CalmVariable.WithOptions.FromTask(
        CalmVarTask.Exec.escript.py3(
            name="",
            filename=os.path.join(
                "scripts", "cluster_dropdown.py"
            ),
        ),
        label="",
        is_mandatory=False,
        is_hidden=False,
        description="",
        regex="^.*$",
        validate_regex=False,
    )  
    subnet_name = CalmVariable.WithOptions.FromTask(
        CalmVarTask.Exec.escript.py3(
            name="",
            filename=os.path.join(
                "scripts", "subnet_dropdown.py"
            ),
        ),
        label="",
        is_mandatory=False,
        is_hidden=False,
        description="",
    )  

    CalmTask.SetVariable.escript.py3(
        name="Get PC_IP and BP_Name",
        filename=os.path.join("scripts", "get_pc_ip_bp_name.py"),
        variables=["PC_IP","bp_name"],
    )

    CalmTask.SetVariable.escript.py3(
        name="VM Name",
        filename=os.path.join("scripts", "gen_vm_name.py"),
        variables=["vm_name"],
    )

    CalmTask.SetVariable.escript.py3(
        name="Get Category UUID",
        filename=os.path.join("scripts", "get_category_uuid.py"),
        variables=["cat_uuids_filter_cluster", 
                   "cat_uuids_filter_subnet",
                   "cat_uuids_filter_image_1",
                   "cat_uuids_filter_image_2"],
    )
    CalmTask.SetVariable.escript.py3(
        name="Select Cluster and Network",
        filename=os.path.join("scripts", "select_cluster_subnet_by_categories_escript.py"),
        variables=["selected_cluster_reference", 
                   "selected_subnet_reference"],
    )
    CalmTask.SetVariable.escript.py3(
        name="Select Image",
        filename=os.path.join("scripts", "select_image_by_categories_escript.py"),
        variables=["selected_image_reference"],
    )

    CalmTask.Exec.escript.py3(
        name="Launch Blueprint",
        filename=os.path.join("scripts", "launch_bp_escript.py"),
    )

class RunbookMetadata(Metadata):
    project = Ref.Project(env_data["NCM"]["project"])

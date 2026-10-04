
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
    Ref.Account(env_data["cred_provider"]),
    resource_type=Ref.Resource_Type(env_data["cred_provider"]),
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
def VMRequest(credentials=[BP_CRED_API_CRED]):

    bp_name = CalmVariable.Simple(
        env_data.get("bp1_name", ""), label="", is_mandatory=False, is_hidden=False, runtime=True, description=""
    )  
    NC_FQDN = CalmVariable.Simple(
        env_data.get("nc_fqdn", ""), label="", is_mandatory=False, is_hidden=False, runtime=True, description=""
    )  
    selection = CalmVariable.WithOptions(
        ["Automatic", "Manual"],
        label="Selection",
        default="Automatic",
        is_mandatory=False,
        is_hidden=False,
        runtime=True,
        description="",
    )  # noqa
    Subnet = CalmVariable.WithOptions.FromTask(
        CalmVarTask.Exec.escript.py3(
            name="",
            filename=os.path.join(
                "scripts", "_Runbook_VMRequest_variable_Subnet_Task_SampleTask.py"
            ),
        ),
        label="",
        is_mandatory=False,
        is_hidden=False,
        description="",
    )  # noqa
    cluster = CalmVariable.WithOptions.FromTask(
        CalmVarTask.Exec.escript.py3(
            name="",
            filename=os.path.join(
                "scripts", "_Runbook_VMRequest_variable_cluster_Task_SampleTask.py"
            ),
        ),
        label="",
        is_mandatory=False,
        is_hidden=False,
        description="",
        regex="^.*$",
        validate_regex=False,
    )  # noqa
    app_type_test = CalmVariable.WithOptions(
        ["JBOSS", "Nginix", "Weblogic"],
        label="APP TYPE",
        default="JBOSS",
        regex="^.*$",
        validate_regex=False,
        is_mandatory=True,
        is_hidden=False,
        runtime=True,
        description="",
    )  # noqa
    win_version = CalmVariable.WithOptions(
        ["2022", "2025"],
        label="Windows OS Version",
        default="2022",
        is_mandatory=False,
        is_hidden=False,
        runtime=True,
        description="",
    )  # noqa
    centos_version = CalmVariable.WithOptions(
        ["9.8", "9.7"],
        label="Centos Version",
        default="9.8",
        is_mandatory=False,
        is_hidden=False,
        runtime=True,
        description="",
    )  # noqa
    rhel_version = CalmVariable.WithOptions(
        ["9.8", "9.7"],
        label="RHEL Version",
        default="9.8",
        regex="^.*$",
        validate_regex=False,
        is_mandatory=False,
        is_hidden=False,
        runtime=True,
        description="",
    )  # noqa
    os_version = CalmVariable.WithOptions(
        ["9.8", "9.7", "2015"],
        label="",
        default="9.8",
        is_mandatory=False,
        is_hidden=False,
        runtime=True,
        description="",
    )  # noqa
    app_type = CalmVariable.Simple(
        "", label="", is_mandatory=False, is_hidden=False, runtime=True, description=""
    )  # noqa
    env = CalmVariable.Simple(
        "", label="", is_mandatory=False, is_hidden=False, runtime=True, description=""
    )  # noqa
    site = CalmVariable.Simple(
        "", label="", is_mandatory=False, is_hidden=False, runtime=True, description=""
    )  # noqa
    tshirt = CalmVariable.Simple(
        "", label="", is_mandatory=False, is_hidden=False, runtime=True, description=""
    )  # noqa
    vcpu = CalmVariable.Simple.int(
        "",
        label="",
        regex="^[\\d]*$",
        validate_regex=False,
        is_mandatory=False,
        is_hidden=False,
        runtime=True,
        description="",
    )  # noqa
    ram = CalmVariable.Simple.int(
        "",
        label="",
        regex="^[\\d]*$",
        validate_regex=False,
        is_mandatory=False,
        is_hidden=False,
        runtime=True,
        description="",
    )  # noqa
    os = CalmVariable.Simple(
        "", label="", is_mandatory=False, is_hidden=False, runtime=True, description=""
    )  # noqa
    pc = CalmVariable.WithOptions.FromTask(
        CalmVarTask.Exec.escript.py3(
            name="",
            filename=os.path.join(
                "scripts", "_Runbook_VMRequest_variable_pc_Task_SampleTask.py"
            ),
        ),
        label="",
        is_mandatory=False,
        is_hidden=False,
        description="",
    )  # noqa

    CalmTask.Exec.escript.py3(
        name="Input Validation",
        filename=os.path.join("scripts", "_Runbook_VMRequest_Task_InputValidation.py"),
    )
    CalmTask.Exec.escript.py3(
        name="Launch Blueprint",
        filename=os.path.join("scripts", "launch_blueprint.py"),
    )

class RunbookMetadata(Metadata):
    project = Ref.Project(env_data["nc_project"])

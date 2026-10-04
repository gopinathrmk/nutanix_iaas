
import json  
import os  

from calm.dsl.builtins import CalmTask as CalmVarTask
from calm.dsl.builtins import *  
from calm.dsl.runbooks import CalmEndpoint as Endpoint

# Secret Variables

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

class Service1(Service):

    pass


class vmcalm_timeResources(AhvVmResources):

    memory = 4
    vCPUs = 2
    cores_per_vCPU = 1
    disks = [
        AhvVmDisk.Disk.Scsi.cloneFromImageService(env_data["pc1_image"], bootable=True)
    ]
    nics = [AhvVmNic.NormalNic.ingress(env_data["pc1_cluster1_subnet"], cluster=env_data["pc1_cluster1"])]

    power_state = "ON"
    boot_type = "LEGACY"


class vmcalm_time(AhvVm):

    name = "vm-@@{calm_time}@@"
    resources = vmcalm_timeResources
    cluster = Ref.Cluster(name=env_data["pc1_cluster1"])


class VM1(Substrate):

    account = Ref.Account(env_data["ncm_account1"])
    os_type = "Linux"
    provider_type = "AHV_VM"
    provider_spec = vmcalm_time

    provider_spec_editables = read_spec(
        os.path.join("specs", "VM1_create_spec_editables.yaml")
    )
    readiness_probe = readiness_probe(
        connection_type="SSH",
        disabled=True,
        retries="5",
        connection_port=22,
        address="@@{platform.status.resources.nic_list[0].ip_endpoint_list[0].ip}@@",
        delay_secs="60",
    )


class Package1(Package):

    services = [ref(Service1)]


class deployment_c95b2376(Deployment):

    min_replicas = "1"
    max_replicas = "1"
    default_replicas = "1"

    packages = [ref(Package1)]
    substrate = ref(VM1)


class Default(Profile):

    deployments = [deployment_c95b2376]

    json = CalmVariable.Simple(
        "", label="", is_mandatory=False, is_hidden=False, runtime=True, description=""
    )

    site = CalmVariable.Simple(
        "", label="", is_mandatory=False, is_hidden=False, runtime=True, description=""
    )

    app_type = CalmVariable.Simple(
        "", label="", is_mandatory=False, is_hidden=False, runtime=True, description=""
    )

    env = CalmVariable.Simple(
        "", label="", is_mandatory=False, is_hidden=False, runtime=True, description=""
    )


class chn_bp(Blueprint):

    services = [Service1]
    packages = [Package1]
    substrates = [VM1]
    profiles = [Default]
    credentials = [BP_CRED_API_CRED]


class BpMetadata(Metadata):

    categories = {"TemplateType": "Vm"}
    project = Ref.Project(env_data["nc_project"])

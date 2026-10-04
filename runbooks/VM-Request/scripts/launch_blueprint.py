import requests
requests.packages.urllib3.disable_warnings()

# Global configuration
VERSION = "4.2"
RETRIES = 3
BACKOFF_FACTOR = 2
DEFAULT_TIMEOUT = 10
API_SERVER = None
BASE_URL = None
SESSION = None

# ================= NC Details =================
NC_API_URL = "ncm.services."+"@@{NC_FQDN}@@"
NC_USER = "@@{API_CRED.username}@@"
NC_PASSWORD = "@@{API_CRED.secret}@@"
bp_name = "@@{bp_name}@@"
app_name = "test-app-200"

def init_client(api_server, username, password, retries=RETRIES, backoff_factor=BACKOFF_FACTOR, default_timeout=DEFAULT_TIMEOUT, version=VERSION):
    global API_SERVER, BASE_URL, RETRIES, BACKOFF_FACTOR, SESSION, VERSION, DEFAULT_TIMEOUT

    API_SERVER = api_server
    #BASE_URL = f"https://{api_server}:9440/api"
    BASE_URL = f"https://{api_server}/api"
    RETRIES = retries
    BACKOFF_FACTOR = backoff_factor
    DEFAULT_TIMEOUT = default_timeout
    VERSION = version

    SESSION = requests.Session()
    SESSION.auth = (username, password)
    SESSION.headers.update({"Content-Type": "application/json"})
    SESSION.verify = False

def process_request(method, endpoint, exit_on_error=True, full_response=False, **kwargs):
    if SESSION is None:
        raise RuntimeError("API client not initialized. Call init_client() first.")
    RETRY_STATUS_CODES = {408, 429, 500, 502, 503, 504}
    url = f"{BASE_URL}{endpoint}"
    error = None

    for attempt in range(1, RETRIES + 1):
        try:
            kwargs.setdefault('timeout', DEFAULT_TIMEOUT)
            response = SESSION.request(method, url, **kwargs)
            response.raise_for_status()

            try:
                data = response.json()
            except ValueError:
                data = response.text

            if not full_response:
                return {"success": True, "status_code": response.status_code, "data": data}
            else:
                return {"success": True, "status_code": response.status_code, "response": response}

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if attempt < RETRIES:
                wait_time = BACKOFF_FACTOR ** (attempt - 1)
                print(f"! Attempt {attempt} failed ({e}). Retrying in {wait_time}s...")
                sleep(wait_time)
                continue
            error = {"success": False, "error": type(e).__name__, "message": str(e), "attempts": attempt}

        except requests.exceptions.HTTPError as e:
            if response.status_code in RETRY_STATUS_CODES and attempt < RETRIES:
                wait_time = BACKOFF_FACTOR ** (attempt - 1)
                sleep(wait_time)
                continue
            error = {"success": False, "error": "HTTPError", "status_code": response.status_code if 'response' in locals() else None, "message": str(e), "attempts": attempt}
            break

        except requests.exceptions.RequestException as e:
            error = {"success": False, "error": "RequestException", "message": str(e), "attempts": attempt}
            break

    if exit_on_error:
        print(f"!!! Fatal: {error}")
        exit(1)
    return error


# Retry status code 
# 429 — Too Many Requests
# 408 — Request Timeout

# These usually indicate temporary backend problems:
# 500 — Internal Server Error
# 502 — Bad Gateway
# 503 — Service Unavailable
# 504 — Gateway Timeout


def list_blueprints(payload={"kind": "blueprint"}):
    endpoint = "/nutanix/v3/blueprints/list"
    response = process_request("POST", endpoint, json=payload, exit_on_error=False)
    # print(f"list_blueprints response: {response}")  # Debugging line
    bps = response.get("data", {}) if response["success"] else []
    return bps

def get_blueprint_by_id(bp_ext_id):
    endpoint = f"/nutanix/v3/blueprints/{bp_ext_id}"
    response = process_request("GET", endpoint, exit_on_error=False)
    bp = response.get("data", {}) if response["success"] else {}
    return bp

def get_blueprint_id_by_name(bp_name):
    endpoint = f"/nutanix/v3/blueprints/list"
    payload={"kind": "blueprint","filter": f"name=={bp_name}"}
    response = process_request("POST", endpoint, json=payload, exit_on_error=False)
    #print(f"get_blueprint_id_by_name response: {response}")  # Debugging line
    bp = response.get("data", {}) if response["success"] else {}
    bp_ext_id = bp.get("entities", [{}])[0].get("status", {}).get("uuid") if bp.get("entities") else None
    return bp_ext_id

def update_blueprint(bp_ext_id, payload):
    endpoint = f"/nutanix/v3/blueprints/{bp_ext_id}"
    response = process_request("PUT", endpoint, json=payload, exit_on_error=False)
    bp = response.get("data", {}) if response["success"] else {}
    return bp

def get_runtime_editables(bp_ext_id):
    endpoint = f"/nutanix/v3/blueprints/{bp_ext_id}/runtime_editables"
    response = process_request("GET", endpoint, exit_on_error=False)
    runtime_editables_response = response.get("data", {}) if response["success"] else {}
    return runtime_editables_response

def monitor_bp_launch_status(bp_ext_id, request_id, max_retries=10):
    if bp_ext_id is None or request_id is None:
        print("Blueprint ID or Request ID is None. Cannot monitor launch status.")
        return {"status": {"state": "failed"}}
    
    endpoint = f"/nutanix/v3/blueprints/{bp_ext_id}/pending_launches/{request_id}"
    for retry in range(max_retries + 1):
        response = process_request("GET", endpoint, exit_on_error=False)
        launch_status = response.get("data", {}) if response["success"] else {}
        status = launch_status.get("status", {}).get("state")
        #pprint(f"Launch status: {status}, Launch details: {launch_status}") # Debugging line
        print(f"Launch status: {status}")

        if status not in ["running", "IN_PROGRESS"]:
            print(f"Final launch status: {status}")
            return launch_status

        if retry < max_retries:
            print("Launch is still in progress. Waiting for 10 seconds before checking again...")
            sleep(10)

    print(f"Maximum retries ({max_retries}) reached. Final launch status: {status}")
    return launch_status


def monitor_app_status(app_uuid, max_retries=10):
    endpoint = f"/nutanix/v3/apps/{app_uuid}"
    for retry in range(max_retries + 1):
        response = process_request("GET", endpoint, exit_on_error=False)
        app_status = response.get("data", {}).get("status", {}).get("state") if response["success"] else None
        print(f"Application status: {app_status}")

        if app_status not in ["provisioning", "IN_PROGRESS"]:
            print(f"Final application status: {app_status}")
            return app_status

        if retry < max_retries:
            print("Application is still in progress. Waiting for 30 seconds before checking again...")
            sleep(30)

    print(f"Maximum retries ({max_retries}) reached. Final application status: {app_status}")
    return app_status

def gen_payload_for_launch(bp_ext_id, runtime_editables_response,app_name,profile="Default"):
    app_profile_ref = {}
    for resource in runtime_editables_response.get("resources", []):
        if resource.get("app_profile_reference", {}).get("name") == profile:
            app_profile_ref = resource.get("app_profile_reference", {})
            runtime_editables = resource.get("runtime_editables", {})
            break

    if app_profile_ref == {}:
        print(f"No app profile found with name '{profile}' in the runtime editables response.")
        return None
    
    payload = {
        "spec": {
            "app_name": app_name,
            "app_profile_reference": app_profile_ref,
            "runtime_editables": runtime_editables
        }
    }
    return payload


def modify_payload_for_launch(payload, app_name=None, vm_name=None, num_sockets=None, num_vcpus_per_socket=None,
                               memory_size_mib=None, cluster_reference=None, subnet_reference=None, 
                               image_reference=None, disk_size_mib=None, app_variable=None):
    if app_name:
        payload["spec"]["app_name"] = app_name

    substrate_spec = payload["spec"]["runtime_editables"].get("substrate_list",[])[0].get("value",{}).get("spec",{})

    if vm_name:
        substrate_spec["name"] = vm_name

    if num_sockets:
        substrate_spec["resources"]["num_sockets"] = num_sockets

    if num_vcpus_per_socket:
        substrate_spec["resources"]["num_vcpus_per_socket"] = num_vcpus_per_socket
    if memory_size_mib:
        substrate_spec["resources"]["memory_size_mib"] = memory_size_mib

    if cluster_reference:
        substrate_spec["cluster_reference"] = cluster_reference

    if subnet_reference:
        substrate_spec["resources"]["nic_list"]["0"]["subnet_reference"] = subnet_reference

    if image_reference:
        substrate_spec["resources"]["disk_list"]["0"]["data_source_reference"] = image_reference
    if disk_size_mib:
        substrate_spec["resources"]["disk_list"]["0"]["disk_size_mib"] = disk_size_mib

    if app_variable:
        variable_list = payload["spec"]["runtime_editables"].get("variable_list",[])
        for variable in variable_list:
            var_name = variable.get("name")
            if var_name in app_variable.keys():
                variable["value"]["value"] = app_variable.get(var_name)

                

def simple_launch_blueprint(bp_ext_id, payload):
    endpoint = f"/nutanix/v3/blueprints/{bp_ext_id}/simple_launch"
    response = process_request("POST", endpoint, json=payload, exit_on_error=False)
    launch_response = response.get("data", {}) if response["success"] else {}
    request_id = launch_response.get("status", {}).get("request_id")

    if not request_id:
        print("Failed to retrieve request_id from the launch response.")
        print(f"Blueprint launch failed.")
        #pprint(response)  # Debugging line
        return None, "failed"

    launch_status=monitor_bp_launch_status(bp_ext_id,request_id)  # Call to get the launch status
    status = launch_status.get("status", {}).get("state")
    app_uuid = launch_status.get("status", {}).get("application_uuid")
    print(f"Launch status: {status}, Application UUID: {app_uuid}")
    return app_uuid, status


def get_app(app_uuid):
    endpoint = f"/nutanix/v3/apps/{app_uuid}"
    response = process_request("GET", endpoint, exit_on_error=False)
    app = response.get("data", {}) if response["success"] else {}
    return app

def main():
    init_client(api_server=NC_API_URL, username=NC_USER, password=NC_PASSWORD)

    bp_ext_id = get_blueprint_id_by_name(bp_name)
    print(bp_ext_id)

    runtime_editables_response = get_runtime_editables(bp_ext_id)
    #pprint(runtime_editables_response)

    payload_for_launch = gen_payload_for_launch(bp_ext_id, runtime_editables_response, app_name=app_name)
    #pprint(payload_for_launch)

    subnet_reference = {
        "kind": "subnet",
        "name": "",
        "uuid": "e0b08efb-7c6f-4eac-b299-c39e2ec2a0a6"
    }

    image_reference = {
        "kind": "image",
        "name": "Rocky-10-GenericCloud-Base.latest.aarch64.qcow2",
        "uuid": "282844c6-4e99-41fd-9c1f-b2c3911d0072"
    }

    cluster_reference = {
        "kind": "cluster",
        "name": "Trigonometry",
        "uuid": "00065b0b-ad7b-1625-6270-3cecef8266c5"
    }
    vm_name = "test-vm-100"

    app_variable = {"site": "blr", "env": "dev", "app_type": "jboss", "json": {"key1": "value1", "key2": "value2"}}

    modify_payload_for_launch(payload_for_launch,app_name=vm_name, vm_name=vm_name, num_sockets=2, num_vcpus_per_socket=2,
                        memory_size_mib=2048, cluster_reference=cluster_reference, subnet_reference=subnet_reference,
                        image_reference=image_reference, disk_size_mib=51200)

    print("Modified payload for launch:")
    #pprint(payload_for_launch)

    app_uuid, status = simple_launch_blueprint(bp_ext_id, payload_for_launch)

    if status == "success":
        print(f"Blueprint launched successfully. Application UUID: {app_uuid}")
        app_status = monitor_app_status(app_uuid)
        if app_status == "running":
            print(f"Application is running successfully. Application UUID: {app_uuid}")
    else:
        print(f"Blueprint launch failed. Status: {status}")


main()
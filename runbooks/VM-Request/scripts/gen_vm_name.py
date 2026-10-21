import requests
requests.packages.urllib3.disable_warnings()

#from time import sleep
# Global configuration
VERSION = "4.2"
BACKOFF_FACTOR = 2
DEFAULT_TIMEOUT = 10
RETRIES = 3
SESSION = None
BASE_URL = None


def init_client(api_server, username, password, retries=RETRIES, backoff_factor=BACKOFF_FACTOR, default_timeout=DEFAULT_TIMEOUT, version=VERSION):
    global API_SERVER, BASE_URL, RETRIES, BACKOFF_FACTOR, SESSION, VERSION, DEFAULT_TIMEOUT

    API_SERVER = api_server
    BASE_URL = f"https://{api_server}:9440/api"
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


def list_vms(params=None, exit_on_error=True):
    response = process_request("GET", f"/vmm/v{VERSION}/ahv/config/vms", params=params, exit_on_error=exit_on_error)
    vms = response.get("data", {}) if response["success"] else []
    return vms


# ================= PC Details =================
PC_IP = "@@{PC_IP}@@"
PC_USER = "@@{API_CRED.username}@@"
PC_PASSWORD = "@@{API_CRED.secret}@@"


app_type = "@@{app_type}@@"
env = "@@{env}@@"
site = "@@{site}@@"


def main():
    
    vm_name = site + "-" + env + "-" + app_type
    vm_name = vm_name.lower()
    # print(vm_name)

    init_client(api_server=PC_IP, username=PC_USER, password=PC_PASSWORD)

    params = {
        "$filter" : f"startswith(name,'{vm_name}')"
    }

    vms = list_vms(params=params)

    total_vms_count = vms.get("metadata", {}).get("totalAvailableResults")
    # print(f"Total VMs in cluster: {total_vms_count}")
    page_loop = (total_vms_count // 100) + 1 if total_vms_count else 0
    # print(f"Page Loop: {page_loop}")
    
    latest_series = 0
    for page in range(page_loop):
        # print("\t\tPage '{}'".format(page+1), end="")  # Print page number
        params = {
            "$filter" : f"startswith(name,'{vm_name}')",
            "$page" : page,
            "$limit" : 100,
        }
        vms = list_vms(params=params).get("data", [])
        print("Found VMs with name ") if vms else None
        for vm in vms:
            print("\t",vm.get("name"))
            parts = vm.get("name").rsplit("-",1)
            if len(parts) ==2 and parts[1].isdigit():
                series = int(parts[1])
                latest_series = max(latest_series,series)

    suffix = latest_series + 1

    vm_name = vm_name + f"-{suffix:03}"
    
    print(f"vm_name={vm_name}")


main()

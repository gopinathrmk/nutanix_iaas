import requests

BACKOFF_FACTOR = 2

DEFAULT_TIMEOUT = 10

RETRIES = 3

SESSION = None

# Global configuration
VERSION = "4.2"

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

BASE_URL = None

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

def get_vm_by_name(name, exit_on_error=True):
    params = {
        "$filter": f"name eq '{name}'"
    }
    response = process_request("GET", f"/vmm/v{VERSION}/ahv/config/vms", params=params, exit_on_error=exit_on_error)
    vm = response.get("data", {}) if response["success"] else {}
    total_matches = vm.get("metadata", {}).get("totalAvailableResults", 0)
    if total_matches == 1:
        return vm.get("data",[])[0]
    else:
        return {}

# ================= PC Details =================
PC_IP = "@@{PC_IP}@@"
PC_USER = "@@{API_CRED.username}@@"
PC_PASSWORD = "@@{API_CRED.secret}@@"
vm_name = "@@{vm_name}@@"


def main():
    init_client(api_server=PC_IP, username=PC_USER, password=PC_PASSWORD)
    vm_response = get_vm_by_name(vm_name)
    if vm_response:
        if vm_response.get("nics") and vm_response.get("nics")[0]:
            ip = vm_response.get("nics")[0].get("nicNetworkInfo").get("ipv4Config").get("ipAddress").get("value")
        else:
            ip = None
        vm_details = {"name": vm_response.get("name"), "ip": ip}
        print(f"vm_details={json.dumps(vm_details)}")
    else:
        print(f"vm_details=VM '{vm_name}' Not Found")

main()

import requests
requests.packages.urllib3.disable_warnings()
# import json # comment for escript

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

def get_category_by_name(key,value, exit_on_error=True):
    params = {
        "$filter": f"tolower(key) eq '{key}' and tolower(value) eq '{value}'"
    }
    response = process_request("GET", f"/prism/v{VERSION}/config/categories", params=params, exit_on_error=exit_on_error)
    category = response.get("data", {}) if response["success"] else {}
    # print(category)
    total_matches = category.get("metadata", {}).get("totalAvailableResults", 0)
    if total_matches == 1:
        return category.get("data",[])[0]
    else:
        return {}

# ================= PC Details =================
PC_IP = "@@{PC_IP}@@"
PC_USER = "@@{API_CRED.username}@@"
PC_PASSWORD = "@@{API_CRED.secret}@@"


app_type = "@@{app_type}@@"
env = "@@{env}@@"
site = "@@{site}@@"
os_name = "@@{os_name}@@"
win_version = "@@{win_version}@@"
lin_version = "@@{lin_version}@@"

def main():
    category_filter_cluster = [{env : app_type }]
    category_filter_subnet = [{env : app_type }]

    os_category = {os_name : win_version} if os_name == "windows" else {os_name : lin_version}
    category_filter_images = [[{env : app_type}, os_category, {"disk":"1"}],[{env : app_type}, os_category, {"disk":"2"}]]

    cat_uuids_filter_cluster = []
    cat_uuids_filter_subnet = []

    init_client(api_server=PC_IP, username=PC_USER, password=PC_PASSWORD)
    for category in category_filter_cluster:
        category_name, category_value = next(iter(category.items()))
        category_data = get_category_by_name(category_name, category_value)
        if category_data:
            cat_uuids_filter_cluster.append(category_data.get("extId"))
        else:
            print(f"!!! Fatal: no category for {category_name}={category_value}")
            exit(1)

    for category in category_filter_subnet:
        category_name, category_value = next(iter(category.items()))
        category_data = get_category_by_name(category_name, category_value)
        if category_data:
            cat_uuids_filter_subnet.append(category_data.get("extId"))
        else:
            print(f"!!! Fatal: no category for {category_name}={category_value}")
            exit(1)

    cat_uuids_filter_images =[]
    for category_filter_image in category_filter_images:
        cat_uuids_filter_image = []
        for category in category_filter_image :
            category_name, category_value = next(iter(category.items()))
            category_data = get_category_by_name(category_name, category_value)
            if category_data:
                cat_uuids_filter_image.append(category_data.get("extId"))
            else:
                print(f"!!! Fatal: no category for {category_name}={category_value}")
                exit(1)
        cat_uuids_filter_images.append(cat_uuids_filter_image)


    print("cat_uuids_filter_cluster=" + json.dumps(cat_uuids_filter_cluster))
    print("cat_uuids_filter_subnet=" + json.dumps(cat_uuids_filter_subnet))
    print("cat_uuids_filter_images=" + json.dumps(cat_uuids_filter_images))

    
main()
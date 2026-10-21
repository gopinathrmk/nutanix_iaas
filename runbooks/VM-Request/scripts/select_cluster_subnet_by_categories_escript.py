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

def list_clusters(params=None, exit_on_error=True):
    response = process_request("GET", f"/clustermgmt/v{VERSION}/config/clusters", params=params, exit_on_error=exit_on_error)
    clusters = response.get("data", {}) if response["success"] else {}
    return clusters

def list_subnets(params=None, exit_on_error=True):
    response = process_request("GET", f"/networking/v{VERSION}/config/subnets", params=params, exit_on_error=exit_on_error)
    subnets = response.get("data", {}) if response["success"] else {}
    return subnets

# ================= PC Details =================
PC_IP = "@@{PC_IP}@@"
PC_USER = "@@{API_CRED.username}@@"
PC_PASSWORD = "@@{API_CRED.secret}@@"

try:
    cat_uuids_filter_cluster = json.loads('@@{cat_uuids_filter_cluster}@@')
    cat_uuids_filter_subnet = json.loads('@@{cat_uuids_filter_subnet}@@')
except json.decoder.JSONDecodeError:
    cat_uuids_filter_cluster = []
    cat_uuids_filter_subnet = []


def main():
    init_client(api_server=PC_IP, username=PC_USER, password=PC_PASSWORD)
    filtered_clusters = []
    selected_cluster_reference = None
    selected_subnet_reference = None


    # Fetch all clusters and filter them based on the provided category UUIDs
    clusters = list_clusters()
    total_clusters = clusters.get("metadata", {}).get("totalAvailableResults", 0)
    page_loop = total_clusters // 100 + 1
    for page in range(page_loop):
        params = {
            "$page": page,
            "$limit": 100
        } 

        clusters = list_clusters(params=params)
        for cluster in clusters.get("data", []):
            cluster_categories = cluster.get("categories", [])
            if set(cat_uuids_filter_cluster).issubset(set(cluster_categories)):
                filtered_clusters.append(cluster)

    print("Filtered Clusters with categories", cat_uuids_filter_cluster)
    for cluster in filtered_clusters:
        print("\t" + cluster.get("name"), cluster.get("extId"))            

    if len(filtered_clusters) == 1:
        selected_cluster_reference = {
            "kind": "cluster",
            "name": filtered_clusters[0].get("name"),
            "uuid": filtered_clusters[0].get("extId")
        }
    elif len(filtered_clusters) > 1:
        print("\nMultiple clusters found with the specified categories. Please refine your category filters.")
        exit(1)
    else:
        print("\nNo clusters found with the specified categories.")
        exit(1)

    print("\nSelected Cluster:", selected_cluster_reference.get("name"))


    # Fetch all subnets and filter them based on the provided category UUIDs and the selected cluster
    params = {
        "$filter" : "clusterReference eq '" + filtered_clusters[0].get("extId") + "'"
    }
    subnets = list_subnets()
    total_subnets = subnets.get("metadata", {}).get("totalAvailableResults", 0)
    page_loop = total_subnets // 100 + 1
    filtered_subnets = []
    for page in range(page_loop):
        params = {
            "$page": page,
            "$limit": 100,
            "$filter" : "clusterReference eq '" + selected_cluster_reference.get("uuid") + "'"
        } 

        subnets = list_subnets(params=params)
        for subnet in subnets.get("data", []):
            subnet_categories = subnet.get("metadata",{}).get("categoryIds", [])
            if set(cat_uuids_filter_subnet).issubset(set(subnet_categories)):
                filtered_subnets.append(subnet)

    # print("\nFiltered Subnets with categories", cat_uuids_filter_subnet)
    # for subnet in filtered_subnets:
    #     print("\t" + subnet.get("name"), subnet.get("extId"))
    # print("")

    if len(filtered_subnets) == 1:
        selected_subnet_reference = {
            "kind": "subnet",
            "name": filtered_subnets[0].get("name"),
            "uuid": filtered_subnets[0].get("extId")
        }
    elif len(filtered_subnets) > 1:
        print("\nMultiple subnets found with the specified categories. Please refine your category filters.")
        exit(1)
    else:
        print("\nNo subnets found with the specified categories.")
        exit(1)

    print("Selected Subnet:", selected_subnet_reference.get("name"),"\n")

    print("selected_cluster_reference=", json.dumps(selected_cluster_reference))
    print("selected_subnet_reference=", json.dumps(selected_subnet_reference))


main()

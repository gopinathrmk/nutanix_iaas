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

def list_images(params=None, exit_on_error=True):
    response = process_request("GET", f"/vmm/v{VERSION}/content/images", params=params, exit_on_error=exit_on_error)
    images = response.get("data", {}) if response["success"] else {}
    return images

# ================= PC Details =================
PC_IP = "@@{PC_IP}@@"
PC_USER = "@@{API_CRED.username}@@"
PC_PASSWORD = "@@{API_CRED.secret}@@"

try:
    cat_uuids_filter_images = json.loads('@@{cat_uuids_filter_images}@@')
except json.decoder.JSONDecodeError:
    print("!!! Fatal: invalid JSON format for cat_uuids_filter_image_1 or cat_uuids_filter_image_2")
    exit(1)


def main():
    init_client(api_server=PC_IP, username=PC_USER, password=PC_PASSWORD)
    selected_image_reference_list = []
    filtered_images_0 = []
    filtered_images_1 = []

    # Fetch all images and filter them based on the provided category UUIDs
    images = list_images()
    total_images = images.get("metadata", {}).get("totalAvailableResults", 0)
    page_loop = total_images // 100 + 1
    for page in range(page_loop):
        params = {
            "$page": page,
            "$limit": 100
        } 

        images = list_images(params=params)
        for image in images.get("data", []):
            image_categories = image.get("categoryExtIds", [])
            if set(cat_uuids_filter_images[0]).issubset(set(image_categories)):
                filtered_images_0.append(image)
            if set(cat_uuids_filter_images[1]).issubset(set(image_categories)):
                filtered_images_1.append(image)

    # print("Filtered Images with categories", cat_uuids_filter_image)
    # for image in filtered_images:
    #     print("\t" + image.get("name"), image.get("extId"))            

    filtered_images_list=[filtered_images_0, filtered_images_1]

    for filtered_images in filtered_images_list:
        if len(filtered_images) == 1:
            selected_image_reference_list.append(
                {"reference" : {
                    "kind": "image",
                    "name": filtered_images[0].get("name"),
                    "uuid": filtered_images[0].get("extId")
                    },
                    "disk_size_mib": round(int(filtered_images[0].get("sizeBytes"))/1024/1024),
                }
            )
        elif len(filtered_images) > 1:
            print("\nMultiple images found with the specified categories. Please refine your category filters." )
            exit(1)
        else:
            print("\nNo images found with the specified categories.")
            exit(1)

    print("selected_image_reference_list=", json.dumps(selected_image_reference_list))

main()

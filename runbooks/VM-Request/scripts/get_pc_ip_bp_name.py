site = "@@{site}@@"
os_name = "@@{os_name}@@"

try:
    PC_details = json.loads('@@{PC_details}@@')
except Exception as e:
    print(f"Error loading PC_details: {e}")
    exit(1)

for pc in PC_details:
    if pc.get("site") == site:
        PC_IP = pc.get("IP")
        break



os_name = os_name if os_name == "windows" else "linux"
bp_name = os_name + "_" + site


print(f"PC_IP={PC_IP}")
print(f"bp_name={bp_name}")

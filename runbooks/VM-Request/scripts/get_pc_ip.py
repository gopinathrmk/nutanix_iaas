site = "@@{site}@@"
try:
    PC_details = json.loads('@@{PC_details}@@')
except Exception as e:
    print(f"Error loading PC_details: {e}")
    exit(1)

for pc in PC_details:
    if pc.get("site") == site:
        PC_IP = pc.get("IP")
        break

print(f"PC_IP={PC_IP}")

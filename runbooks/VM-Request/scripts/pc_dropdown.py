
#print("PC-M7, PC-M8")
pc_details = json.loads('@@{PC_details}@@')

#print(type(pc_details))
#print(pc_details)

pc_list = ""
for pc in pc_details:
  pc_list = pc_list + pc.get("name") + ","

pc_list = pc_list.rstrip(",")
print(pc_list)
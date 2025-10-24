import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
import json
import time
import os
import restconf_final  # Module for RESTCONF
import netconf_final   # NEW: Module for NETCONF
import netmiko_final
import ansible_final
from dotenv import load_dotenv

#######################################################################################
# 2. Assign environment variables
load_dotenv()
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
roomIdToGetMessages = os.environ.get("WEBEX_ROOM_ID")
print(f"Current token: {ACCESS_TOKEN}")
print(f"Current Room ID: {roomIdToGetMessages}")

# --- NEW: Define project constants ---
STUDENT_ID = "66070046"
VALID_IPS = ["10.0.15.61", "10.0.15.62", "10.0.15.63", "10.0.15.64", "10.0.15.65"]

# --- NEW: State variables for the bot ---
# (ตัวแปรนอก Loop เพื่อให้บอทจดจำค่าได้)
current_method = None  # Will store 'restconf' or 'netconf'

while True:
    time.sleep(1) # หน่วงเวลา 1 วินาที

    getParameters = {"roomId": roomIdToGetMessages, "max": 1}
    getHTTPHeader = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

    # 4. Get the latest message
    try:
        r = requests.get(
            "https://webexapis.com/v1/messages",
            params=getParameters,
            headers=getHTTPHeader,
        )
        if not r.status_code == 200:
            print(f"Error getting messages: {r.status_code}")
            continue # ข้ามรอบนี้ไป

        json_data = r.json()
        if len(json_data["items"]) == 0:
            print("No messages in room.")
            continue # ข้ามรอบนี้ไป

        messages = json_data["items"]
        message = messages[0]["text"]
        print(f"Received message: {message}")

    except Exception as e:
        print(f"Error (Get Message): {e}")
        continue

    # 5. --- NEW: Command Parsing Logic ---
    if message.startswith(f"/{STUDENT_ID} "):
        
        # แยกส่วนคำสั่ง
        try:
            parts = message.split(f"/{STUDENT_ID} ")[1].split()
        except IndexError:
            parts = []

        if not parts:
            responseMessage = "Error: No command found."
            continue # ข้ามไป ไม่ต้อง post

        # --- Logic for 1 argument commands (e.g., /ID restconf or /ID showrun) ---
        elif len(parts) == 1:
            arg1 = parts[0].lower()

            if arg1 == "restconf":
                current_method = "restconf"
                responseMessage = "Ok: Restconf"
            elif arg1 == "netconf":
                current_method = "netconf"
                responseMessage = "Ok: Netconf"
            elif arg1 in VALID_IPS:
                responseMessage = "Error: No command found."
            
            # --- Handle 'Part 1' commands (create, delete, etc.) ---
            elif arg1 in ["create", "delete", "enable", "disable", "status"]:
                if not current_method:
                    responseMessage = "Error: No method specified"
                else:
                    responseMessage = "Error: No IP specified"
            
            # --- Handle other commands (gigabit_status, showrun) ---
            elif arg1 == "gigabit_status":
                # (ใช้ logic เดิม ที่ hardcode IP ใน netmiko_final.py)
                responseMessage = netmiko_final.gigabit_status()
            elif arg1 == "showrun":
                # (ใช้ logic เดิม ที่ hardcode IP ใน ansible)
                response = ansible_final.showrun()
                responseMessage = response["msg"]
            else:
                responseMessage = "Error: No command or unknown command"

        # --- Logic for 2+ argument commands (e.g., /ID 10.0.15.61 create) ---
        elif len(parts) >= 2:
            arg1 = parts[0].lower()
            arg2 = parts[1].lower()

            if arg1 in VALID_IPS:
                target_ip = arg1
                command = arg2

                if command in ["create", "delete", "enable", "disable", "status"]:
                    if not current_method:
                        responseMessage = "Error: No method specified"
                    
                    # --- EXECUTION: RESTCONF ---
                    elif current_method == "restconf":
                        if command == "create":
                            responseMessage = restconf_final.create(target_ip)
                        elif command == "delete":
                            responseMessage = restconf_final.delete(target_ip)
                        elif command == "enable":
                            responseMessage = restconf_final.enable(target_ip)
                        elif command == "disable":
                            responseMessage = restconf_final.disable(target_ip)
                        elif command == "status":
                            responseMessage = restconf_final.status(target_ip)

                    # --- EXECUTION: NETCONF ---
                    elif current_method == "netconf":
                        if command == "create":
                            responseMessage = netconf_final.create(target_ip)
                        elif command == "delete":
                            responseMessage = netconf_final.delete(target_ip)
                        elif command == "enable":
                            responseMessage = netconf_final.enable(target_ip)
                        elif command == "disable":
                            responseMessage = netconf_final.disable(target_ip)
                        elif command == "status":
                            responseMessage = netconf_final.status(target_ip)
                
                else:
                    responseMessage = f"Error: Unknown command '{command}' for IP {target_ip}"
            else:
                responseMessage = "Error: Invalid IP or command format."

        # 6. --- Post the message to Webex ---
        
        # (ส่วนนี้เหมือนเดิมเกือบทั้งหมด แค่เปลี่ยนตัวแปร command เป็น arg1)
        command_to_check = parts[0].lower() # ใช้ตัวแปรใหม่

        if command_to_check == "showrun" and responseMessage == "ok":
            print("Sending show running config")
            filename = f"./backups/show_run_{STUDENT_ID}_CSR1KV-Pod1-1.txt"
            
            try:
                with open(filename, "rb") as fileobject:
                    postData = {
                        "roomId": roomIdToGetMessages,
                        "text": "show running config",
                        "files": (os.path.basename(filename), fileobject, "text/plain"),
                    }
                    postData = MultipartEncoder(postData)
                    HTTPHeaders = {
                        "Authorization": f"Bearer {ACCESS_TOKEN}",
                        "Content-Type": postData.content_type,
                    }
            except FileNotFoundError:
                print(f"Error: Backup file {filename} not found.")
                responseMessage = f"Error: Ansible OK, but backup file {filename} not found."
                # Fallback to text message
                command_to_check = "fallback" # บังคับให้ไปที่ else

        if command_to_check != "showrun" or responseMessage != "ok":
            postData = {"roomId": roomIdToGetMessages, "text": responseMessage}
            postData = json.dumps(postData)
            HTTPHeaders = {
                "Authorization": f"Bearer {ACCESS_TOKEN}",
                "Content-Type": "application/json",
            }

        # Send the POST request
        try:
            r = requests.post(
                "https://webexapis.com/v1/messages",
                data=postData,
                headers=HTTPHeaders,
            )
            if not r.status_code == 200:
                print(f"Error posting message: {r.status_code} {r.text}")
        except Exception as e:
            print(f"Error (Post Message): {e}")
#######################################################################################
# File: ipa2025_final.py
# Description: Main ChatOps bot script
#######################################################################################

# 1. Import libraries
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
import json
import time
import os
import restconf_final  # Module for RESTCONF
import netconf_final   # Module for NETCONF
import netmiko_final
import ansible_final
from dotenv import load_dotenv

#######################################################################################
# 2. Assign environment variables
load_dotenv()
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
roomIdToGetMessages = os.environ.get("WEBEX_ROOM_ID")

# --- MODIFIED: อ่านค่าจาก .env ให้ครบ ---
STUDENT_ID = os.environ.get("STUDENT_ID")
ANSIBLE_ROUTER_NAME = os.environ.get("ANSIBLE_ROUTER_NAME") 

print(f"Current token: {ACCESS_TOKEN}")
print(f"Current Room ID: {roomIdToGetMessages}")
print(f"Student ID: {STUDENT_ID}")

# --- Constants ---
VALID_IPS = ["10.0.15.61", "10.0.15.62", "10.0.15.63", "10.0.15.64", "10.0.15.65"]

# --- State variables for the bot ---
current_method = None  # Will store 'restconf' or 'netconf'
last_message_id = None # ใช้อ้างอิง message ล่าสุดที่อ่านแล้ว

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
            continue 

        json_data = r.json()
        if len(json_data["items"]) == 0:
            print("No messages in room.")
            continue 

        messages = json_data["items"]
        message_id = messages[0]["id"]
        
        # --- MODIFIED: ตรวจสอบว่า message นี้ถูกอ่านไปหรือยัง ---
        if message_id == last_message_id:
            continue # ถ้าเป็น ID เดียวกับรอบที่แล้ว ให้ข้ามไป
        
        # ถ้าเป็น message ใหม่, ให้อัปเดต ID และทำงานต่อ
        last_message_id = message_id 
        message = messages[0]["text"]
        print(f"Received message: {message}")

    except Exception as e:
        print(f"Error (Get Message): {e}")
        continue

    # 5. --- Command Parsing Logic ---
    if message.startswith(f"/{STUDENT_ID} "):
        
        responseMessage = "" # Reset response message
        
        try:
            parts = message.split(f"/{STUDENT_ID} ")[1].split()
        except IndexError:
            parts = []

        if not parts:
            responseMessage = "Error: No command found."
            
        # --- Logic for 1 argument commands ---
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
            
            elif arg1 in ["create", "delete", "enable", "disable", "status"]:
                if not current_method:
                    responseMessage = "Error: No method specified"
                else:
                    responseMessage = "Error: No IP specified"
            
            elif arg1 == "gigabit_status":
                responseMessage = netmiko_final.gigabit_status()
            elif arg1 == "showrun":
                response = ansible_final.showrun()
                responseMessage = response["msg"]
            else:
                responseMessage = "Error: No command or unknown command"

        # --- Logic for 2+ argument commands ---
        elif len(parts) >= 2:
            arg1 = parts[0].lower()
            arg2 = parts[1].lower()

            if arg1 in VALID_IPS:
                target_ip = arg1
                command = arg2

                if command in ["create", "delete", "enable", "disable", "status"]:
                    if not current_method:
                        responseMessage = "Error: No method specified"
                    
                    # --- EXECUTION: RESTCONF (FIXED) ---
                    elif current_method == "restconf":
                        if command == "create":
                            responseMessage = restconf_final.create(target_ip, STUDENT_ID)
                        elif command == "delete":
                            responseMessage = restconf_final.delete(target_ip, STUDENT_ID)
                        elif command == "enable":
                            responseMessage = restconf_final.enable(target_ip, STUDENT_ID)
                        elif command == "disable":
                            responseMessage = restconf_final.disable(target_ip, STUDENT_ID)
                        elif command == "status":
                            responseMessage = restconf_final.status(target_ip, STUDENT_ID)

                    # --- EXECUTION: NETCONF (FIXED) ---
                    elif current_method == "netconf":
                        if command == "create":
                            responseMessage = netconf_final.create(target_ip, STUDENT_ID)
                        elif command == "delete":
                            responseMessage = netconf_final.delete(target_ip, STUDENT_ID)
                        elif command == "enable":
                            responseMessage = netconf_final.enable(target_ip, STUDENT_ID)
                        elif command == "disable":
                            responseMessage = netconf_final.disable(target_ip, STUDENT_ID)
                        elif command == "status":
                            responseMessage = netconf_final.status(target_ip, STUDENT_ID)
                
                else:
                    responseMessage = f"Error: Unknown command '{command}' for IP {target_ip}"
            else:
                responseMessage = "Error: Invalid IP or command format."

        # 6. --- Post the message to Webex ---
        
        # ถ้าไม่มี responseMessage (เช่น parse ไม่ผ่าน) ก็ไม่ต้องส่ง
        if not responseMessage:
            continue

        command_to_check = parts[0].lower() 
        
        # --- MODIFIED: ตรวจสอบ showrun ให้ถูกต้อง ---
        # (ต้องเช็คว่า command คือ 'showrun' จริงๆ ไม่ใช่ 'create')
        is_showrun = False
        if len(parts) == 1 and parts[0].lower() == "showrun":
            is_showrun = True


        if is_showrun and responseMessage == "ok":
            print("Sending show running config")
            
            # --- MODIFIED: ใช้ตัวแปรจาก .env ---
            filename = f"./backups/show_run_{STUDENT_ID}_{ANSIBLE_ROUTER_NAME}.txt" 
            
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
                is_showrun = False # บังคับให้ไปที่ else
        
        # --- MODIFIED: ส่งข้อความแบบ text (กรณีที่ไม่ใช่ showrun หรือ showrunล้มเหลว) ---
        if not is_showrun or responseMessage != "ok":
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
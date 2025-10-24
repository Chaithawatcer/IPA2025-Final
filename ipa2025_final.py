# 1. Import libraries
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
import json
import time
import os
import restconf_final  # Module for RESTCONF
import netconf_final   # Module for NETCONF
import netmiko_final   # Module for Netmiko
import ansible_final   # Module for Ansible
from dotenv import load_dotenv

#######################################################################################
# 2. Assign environment variables
load_dotenv()
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
roomIdToGetMessages = os.environ.get("WEBEX_ROOM_ID")
print(f"Current token: {ACCESS_TOKEN}")
print(f"Current Room ID: {roomIdToGetMessages}")

# --- NEW: Define project constants ---
# TODO: เปลี่ยนเป็นรหัสนักศึกษาของคุณ (จากในภาพคือ 66070046)
STUDENT_ID = "66070046" 
VALID_IPS = ["10.0.15.61", "10.0.15.62", "10.0.15.63", "10.0.15.64", "10.0.15.65", "10.0.15.45"]

# --- NEW: State variables for the bot ---
current_method = None  # Will store 'restconf' or 'netconf'
last_message_id = None # ป้องกันบอทอ่านข้อความเดิมซ้ำ

while True:
    time.sleep(1) 

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
        
        # --- NEW: Prevent reading the same message ---
        if message_id == last_message_id:
            continue # ข้ามไป ถ้าเป็นข้อความเดิม
        
        last_message_id = message_id # บันทึกข้อความล่าสุด
        message = messages[0]["text"]
        print(f"Received message: {message}")

    except Exception as e:
        print(f"Error (Get Message): {e}")
        continue

    # 5. --- NEW: Command Parsing Logic ---
    if message.startswith(f"/{STUDENT_ID} "):
        
        try:
            parts = message.split(f"/{STUDENT_ID} ")[1].split()
        except IndexError:
            parts = []

        responseMessage = None # ตั้งค่าเริ่มต้น

        if not parts:
            responseMessage = "Error: No command found."
        
        # --- Logic for 1-arg commands (restconf, netconf) ---
        elif len(parts) == 1:
            arg1 = parts[0].lower()
            if arg1 == "restconf":
                current_method = "restconf"
                responseMessage = "Ok: Restconf"
            elif arg1 == "netconf":
                current_method = "netconf"
                responseMessage = "Ok: Netconf"
            elif arg1 in ["create", "delete", "enable", "disable", "status", "motd", "showrun", "gigabit_status"]:
                if not current_method and arg1 in ["create", "delete", "enable", "disable", "status"]:
                    responseMessage = "Error: No method specified"
                else:
                    responseMessage = "Error: No IP specified"
            else:
                responseMessage = "Error: No command or unknown command"
        
        # --- Logic for 2+ arg commands (IP + command + [data]) ---
        elif len(parts) >= 2:
            arg1 = parts[0].lower() # This should be the IP
            arg2 = parts[1].lower() # This is the command
            
            if arg1 in VALID_IPS:
                target_ip = arg1
                command = arg2
                
                # --- Part 1 Commands (create, delete, etc.) ---
                if command in ["create", "delete", "enable", "disable", "status"]:
                    if not current_method:
                        responseMessage = "Error: No method specified"
                    
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
                
                # --- NEW: Part 2 Commands (motd, showrun, gigabit_status) ---
                elif command == "motd":
                    if len(parts) > 2:
                        # SET MOTD (e.g., /ID IP motd message here)
                        message_text = " ".join(parts[2:]) # เอาข้อความทั้งหมด
                        response = ansible_final.set_motd(target_ip, message_text)
                        responseMessage = response["msg"] # "Ok: success" or error
                    else:
                        # GET MOTD (e.g., /ID IP motd)
                        responseMessage = netmiko_final.get_motd(target_ip)
                
                elif command == "showrun":
                    response = ansible_final.showrun(target_ip, STUDENT_ID)
                    responseMessage = response["msg"] # "ok" or error
                
                elif command == "gigabit_status":
                    responseMessage = netmiko_final.gigabit_status(target_ip)
                
                else:
                    responseMessage = f"Error: Unknown command '{command}'"
            
            else: # arg1 is not a valid IP
                responseMessage = "Error: Invalid IP or command format. Must be /ID IP COMMAND"

        # 6. --- Post the message to Webex ---
        
        # ถ้าไม่มี responseMessage (เช่น บอทเจอข้อความตัวเอง) ก็ไม่ต้องทำอะไร
        if not responseMessage:
            continue
            
        # ตรวจสอบว่า command คือ showrun และสำเร็จหรือไม่
        command_to_check = parts[1].lower() if len(parts) >= 2 else ""
        target_ip_for_file = parts[0].lower() if len(parts) >= 2 else ""

        if command_to_check == "showrun" and responseMessage == "ok":
            print(f"Sending show running config from {target_ip_for_file}")
            # --- MODIFIED: Dynamic filename ---
            filename = f"./backups/show_run_{STUDENT_ID}_{target_ip_for_file}.txt"
            
            try:
                with open(filename, "rb") as fileobject:
                    postData = {
                        "roomId": roomIdToGetMessages,
                        "text": f"show running config from {target_ip_for_file}",
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
            # หลังโพสต์แล้ว ให้ set last_message_id เป็นของบอท
            # เพื่อป้องกันบอทอ่านข้อความตัวเองในรอบถัดไป
            if r.status_code == 200:
                last_message_id = r.json()["id"]
            else:
                 print(f"Error posting message: {r.status_code} {r.text}")
        except Exception as e:
            print(f"Error (Post Message): {e}")
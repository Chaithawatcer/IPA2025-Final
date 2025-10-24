import json
import requests
import os  # Import os
from dotenv import load_dotenv  # Import dotenv

# ปิด warning เวลา request HTTPS แบบไม่ verify
requests.packages.urllib3.disable_warnings()

# โหลดตัวแปรจาก .env
load_dotenv()

# --- MODIFIED: อ่าน credentials จาก .env ---
studentID = "66070046"
ROUTER_USERNAME = os.environ.get("ROUTER_USERNAME")
ROUTER_PASSWORD = os.environ.get("ROUTER_PASSWORD")
basicauth = (ROUTER_USERNAME, ROUTER_PASSWORD)

# the RESTCONF HTTP headers
headers = {
    "Accept": "application/yang-data+json",
    "Content-Type": "application/yang-data+json",
}

# --- MODIFIED: ทุกฟังก์ชันรับ target_ip และ studentID ---

def create(target_ip, studentID):
    """
    สร้าง Loopback interface ผ่าน RESTCONF
    """
    api_url = f"https://{target_ip}/restconf/data"
    
    yangConfig = {
        "ietf-interfaces:interface": {
            "name": f"Loopback{studentID}",
            "type": "iana-if-type:softwareLoopback",
            "enabled": True,
            "ietf-ip:ipv4": {
                "address": [{"ip": "172.0.46.1", "netmask": "255.255.255.0"}]
            },
            "ietf-ip:ipv6": {},
        }
    }
    
    try:
        resp = requests.put(
            f"{api_url}/ietf-interfaces:interfaces/interface=Loopback{studentID}",  
            data=json.dumps(yangConfig),  
            auth=basicauth,  
            headers=headers,  
            verify=False,
            timeout=10 # เพิ่ม Timeout ป้องกันการค้าง
        )
        if(resp.status_code == 201):
            return f"Interface loopback {studentID} is created successfully (using Restconf)"
        else:
            return f"Cannot create: Interface loopback {studentID} (Error {resp.status_code}) (using Restconf)"
    except requests.exceptions.ConnectionError as e:
        return f"Cannot create: Connection Error to {target_ip} (using Restconf)"
    except Exception as e:
        return f"Cannot create: Interface loopback {studentID} (Error: {e}) (using Restconf)"


def delete(target_ip, studentID):
    """
    ลบ Loopback interface ผ่าน RESTCONF
    """
    api_url = f"https://{target_ip}/restconf/data"
    
    try:
        resp = requests.delete(
            f"{api_url}/ietf-interfaces:interfaces/interface=Loopback{studentID}",  
            auth=basicauth,  
            headers=headers,  
            verify=False,
            timeout=10
        )
        if(resp.status_code == 204):
            return f"Interface loopback {studentID} is deleted successfully (using Restconf)"
        else:
            # 404 คือไม่มีให้ลบ ก็ถือว่าสำเร็จ
            return f"Cannot delete: Interface loopback {studentID} (Error {resp.status_code}) (using Restconf)"
    except requests.exceptions.ConnectionError as e:
        return f"Cannot delete: Connection Error to {target_ip} (using Restconf)"
    except Exception as e:
        return f"Cannot delete: Interface loopback {studentID} (Error: {e}) (using Restconf)"


def enable(target_ip, studentID):
    """
    เปิด (no shutdown) Loopback interface ผ่าน RESTCONF (PATCH)
    """
    api_url = f"https://{target_ip}/restconf/data"
    
    # เราจะส่งข้อมูลเฉพาะส่วนที่ต้องการแก้ (enabled: true)
    # เราจะ PATCH ไปที่ endpoint ของ "enabled" โดยตรง
    patch_data = {"ietf-interfaces:enabled": True}
    
    try:
        resp = requests.patch(
            f"{api_url}/ietf-interfaces:interfaces/interface=Loopback{studentID}/enabled",  
            data=json.dumps(patch_data),  
            auth=basicauth,  
            headers=headers,  
            verify=False,
            timeout=10
        )
        if(resp.status_code == 204): # 204 No Content คือสำเร็จสำหรับ PATCH
            return f"Interface loopback {studentID} is enabled successfully (using Restconf)"
        else:
            return f"Cannot enable: Interface loopback {studentID} (Error {resp.status_code}) (using Restconf)"
    except requests.exceptions.ConnectionError as e:
        return f"Cannot enable: Connection Error to {target_ip} (using Restconf)"
    except Exception as e:
        return f"Cannot enable: Interface loopback {studentID} (Error: {e}) (using Restconf)"


def disable(target_ip, studentID):
    """
    ปิด (shutdown) Loopback interface ผ่าน RESTCONF (PATCH)
    """
    api_url = f"https://{target_ip}/restconf/data"
    
    # เราจะส่งข้อมูลเฉพาะส่วนที่ต้องการแก้ (enabled: false)
    patch_data = {"ietf-interfaces:enabled": False}

    try:
        resp = requests.patch(
            f"{api_url}/ietf-interfaces:interfaces/interface=Loopback{studentID}/enabled",  
            data=json.dumps(patch_data),  
            auth=basicauth,  
            headers=headers,  
            verify=False,
            timeout=10
        )
        if(resp.status_code == 204):
            return f"Interface loopback {studentID} is shutdowned successfully (using Restconf)"
        else:
            return f"Cannot shutdown: Interface loopback {studentID} (Error {resp.status_code}) (using Restconf)"
    except requests.exceptions.ConnectionError as e:
        return f"Cannot shutdown: Connection Error to {target_ip} (using Restconf)"
    except Exception as e:
        return f"Cannot shutdown: Interface loopback {studentID} (Error: {e}) (using Restconf)"

def status(target_ip, studentID):
    """
    ตรวจสอบสถานะ (operational state) ของ Loopback interface ผ่าน RESTCONF
    """
    api_url = f"https://{target_ip}/restconf/data"
    
    try:
        resp = requests.get(
            f"{api_url}/ietf-interfaces:interfaces-state/interface=Loopback{studentID}",
            auth=basicauth,
            headers=headers,
            verify=False,
            timeout=10
        )

        if(resp.status_code == 200):
            response_json = resp.json()
            # ตรวจสอบ key ก่อนว่ามีอยู่จริง
            if "ietf-interfaces:interface" in response_json:
                admin_status = response_json["ietf-interfaces:interface"].get("admin-status", "unknown")
                oper_status = response_json["ietf-interfaces:interface"].get("oper-status", "unknown")
                
                if admin_status == 'up' and oper_status == 'up':
                    return f"Interface loopback {studentID} is enabled (checked by Restconf)"
                else:
                    return f"Interface loopback {studentID} is disabled (checked by Restconf)"
            else:
                 return f"No Interface loopback {studentID} (checked by Restconf)"
        
        elif(resp.status_code == 404):
            return f"No Interface loopback {studentID} (checked by Restconf)"
        else:
            return f"Undefined Error (Error {resp.status_code}) (checked by Restconf)"
    except requests.exceptions.ConnectionError as e:
        return f"Cannot get status: Connection Error to {target_ip} (using Restconf)"
    except Exception as e:
        return f"Undefined Error (Error: {e}) (checked by Restconf)"
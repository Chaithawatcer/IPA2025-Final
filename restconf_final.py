import json
import requests
requests.packages.urllib3.disable_warnings()

headers = {
    "Accept": "application/yang-data+json",
    "Content-Type": "application/yang-data+json",
}
basicauth = ("admin", "cisco")
# ลบ global studentID = "..." จากตรงนี้

# --- MODIFIED: ฟังก์ชันทั้งหมดรับ studentID เป็นอาร์กิวเมนต์ ---

def create(target_ip, studentID):
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
            timeout=10
        )
        if(resp.status_code == 201):
            return f"Interface loopback {studentID} is created successfully (using Restconf)"
        else:
            return f"Cannot create: Interface loopback {studentID} (Error {resp.status_code}) (using Restconf)"
    except Exception as e:
        return f"Cannot create: Interface loopback {studentID} (Error: {e}) (using Restconf)"

def delete(target_ip, studentID):
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
            return f"Cannot delete: Interface loopback {studentID} (Error {resp.status_code}) (using Restconf)"
    except Exception as e:
        return f"Cannot delete: Interface loopback {studentID} (Error: {e}) (using Restconf)"

def enable(target_ip, studentID):
    api_url = f"https://{target_ip}/restconf/data"
    
    try:
        resp = requests.patch(
            f"{api_url}/ietf-interfaces:interfaces/interface=Loopback{studentID}/enabled",
            data=json.dumps({"ietf-interfaces:enabled": True}),
            auth=basicauth,
            headers=headers,
            verify=False,
            timeout=10
        )
        if(resp.status_code == 204):
            return f"Interface loopback {studentID} is enabled successfully (using Restconf)"
        else:
            return f"Cannot enable: Interface loopback {studentID} (Error {resp.status_code}) (using Restconf)"
    except Exception as e:
        return f"Cannot enable: Interface loopback {studentID} (Error: {e}) (using Restconf)"

def disable(target_ip, studentID):
    api_url = f"https://{target_ip}/restconf/data"
    
    try:
        resp = requests.patch(
            f"{api_url}/ietf-interfaces:interfaces/interface=Loopback{studentID}/enabled",
            data=json.dumps({"ietf-interfaces:enabled": False}),
            auth=basicauth,
            headers=headers,
            verify=False,
            timeout=10
        )
        if(resp.status_code == 204):
            return f"Interface loopback {studentID} is shutdowned successfully (using Restconf)"
        else:
            return f"Cannot shutdown: Interface loopback {studentID} (Error {resp.status_code}) (using Restconf)"
    except Exception as e:
        return f"Cannot shutdown: Interface loopback {studentID} (Error: {e}) (using Restconf)"

def status(target_ip, studentID):
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
            admin_status = response_json["ietf-interfaces:interface"]["admin-status"]
            oper_status = response_json["ietf-interfaces:interface"]["oper-status"]
            if admin_status == 'up' and oper_status == 'up':
                return f"Interface loopback {studentID} is enabled (checked by Restconf)"
            else:
                return f"Interface loopback {studentID} is disabled (checked by Restconf)"
        elif(resp.status_code == 404):
            return f"No Interface loopback {studentID} (checked by Restconf)"
        else:
            return f"Undefined Error (Error {resp.status_code}) (checked by Restconf)"
    except Exception as e:
        return f"Undefined Error (Error: {e}) (checked by Restconf)"
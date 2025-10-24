from netmiko import ConnectHandler
from pprint import pprint
import re # <-- Import Regex มาใช้งาน

# TODO: ควรย้ายไปเก็บใน .env
username = "admin"
password = "cisco"

def get_device_params(target_ip):
    """
    Helper function เพื่อสร้าง params ในการเชื่อมต่อ
    (เพิ่ม 'secret' เข้าไป เพื่อให้แน่ใจว่าเข้า enable mode)
    """
    return {
        "device_type": "cisco_ios",
        "ip": target_ip,
        "username": username,
        "password": password,
        "secret": password, # <-- เพิ่มบรรทัดนี้
    }

# ---  FIX 3: แก้ไข get_motd ให้ใช้ 'show run' + 'Regex' ---
def get_motd(target_ip):
    """
    ใช้ Netmiko และ 'show running-config'
    (Parse ด้วย Regex ซึ่งเสถียรที่สุด)
    """
    device_params = get_device_params(target_ip)
    
    try:
        with ConnectHandler(**device_params) as ssh:
            # รัน 'show run' แบบธรรมดา (ไม่ใช้ textfsm)
            result = ssh.send_command("show running-config")
            
            # --- LOGIC ใหม่: ใช้ Regex ---
            #
            # Regex นี้จะหา "banner motd (ตัวคั่น1)(ข้อความ)(ตัวคั่น1)"
            # re.DOTALL ทำให้ . (dot) สามารถหมายถึง \n (ขึ้นบรรทัดใหม่) ได้
            #
            match = re.search(r"banner motd (.)(.*?)\1", result, re.DOTALL)
            
            if match:
                # match.group(2) คือ (.*?) หรือ "ข้อความ" ที่อยู่ข้างใน
                message = match.group(2).strip() # .strip() เพื่อลบ \n ที่ติดมา
                return message
            else:
                # ถ้า Regex หาไม่เจอเลย
                return "Error: No MOTD Configured"
            # --- จบ LOGIC Regex ---
            
    except Exception as e:
        return f"Error connecting to {target_ip}: {e}"


# --- (ฟังก์ชัน gigabit_status เหมือนเดิม) ---
def gigabit_status(target_ip):
    # (โค้ด gigabit_status เดิมของคุณ)
    device_params = {
        "device_type": "cisco_ios_telnet",
        "ip": target_ip,
        "username": username,
        "password": password,
        "secret": password, # <-- เพิ่ม secret ตรงนี้ด้วย
    }

    ans = "" 
    try:
        with ConnectHandler(**device_params) as ssh:
            gi_up, gi_down, gi_admin_down = 0, 0, 0
            lo_up, lo_down, lo_admin_down = 0, 0, 0
            
            result = ssh.send_command("sh int", use_textfsm=True)
            for status in result:
                
                if status["interface"].startswith("GigabitEthernet"):
                    ans += f"{status['interface']} {status['link_status']}, " 
                    if status['link_status'] == "up":
                        gi_up += 1
                    elif status['link_status'] == "down":
                        gi_down += 1
                    elif status['link_status'] == "administratively down":
                        gi_admin_down += 1
                
                elif status["interface"].startswith("Loopback"):
                    if status['link_status'] == "up":
                        lo_up += 1
                    elif status['link_status'] == "down":
                        lo_down += 1
                    elif status['link_status'] == "administratively down":
                        lo_admin_down += 1

            if ans:
                ans = ans[:-2] 
            else:
                ans = "No Gigabit Interfaces found"
            
            ans_summary = f"Gi: {gi_up} up, {gi_down} down, {gi_admin_down} admin-down | Lo: {lo_up} up, {lo_down} down, {lo_admin_down} admin-down"
            
            return f"{ans} -> {ans_summary}"
            
    except Exception as e:
        return f"Error connecting to {target_ip}: {e}"
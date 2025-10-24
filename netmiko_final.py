from netmiko import ConnectHandler
from pprint import pprint
import re # Import regex

# TODO: ควรย้ายไปเก็บใน .env
username = "admin"
password = "cisco"

def get_device_params(target_ip):
    """
    Helper function เพื่อสร้าง params ในการเชื่อมต่อ
    (ใช้ cisco_ios แทน telnet เพื่อให้ใช้ SSH ได้)
    """
    return {
        "device_type": "cisco_ios",
        "ip": target_ip,
        "username": username,
        "password": password,
    }

# ---  FIX: แก้ไข get_motd ให้เสถียรด้วย logic ใหม่ ---
def get_motd(target_ip):
    """
    ใช้ Netmiko และ 'show banner motd'
    (ใช้ logic การ parse ใหม่ที่ทนทานกว่าเดิม)
    """
    device_params = get_device_params(target_ip)
    try:
        with ConnectHandler(**device_params) as ssh:
            # ใช้ 'show banner motd' ซึ่งตรงไปตรงมา และไม่ยุ่งกับ textfsm
            result = ssh.send_command("show banner motd")
            
            if "% No banner configured" in result or not result:
                return "Error: No MOTD Configured"
            
            # --- LOGIC ใหม่ เริ่มตรงนี้ ---
            
            # 1. หาจุดเริ่มต้นของ MOTD (ตัด header ทิ้ง)
            try:
                # หาบรรทัดใหม่บรรทัดแรก
                first_newline = result.index('\n')
                # เอาทุกอย่าง *หลัง* header
                message_with_footer = result[first_newline+1:]
            except ValueError:
                return "Error: Could not parse MOTD header"

            # 2. ตัด footer (บรรทัดสุดท้าย) ทิ้ง
            lines = message_with_footer.splitlines()
            
            if not lines:
                return "" # MOTD ว่างเปล่า (เช่น มีแค่ header กับ footer)
                
            # MOTD คือทุกบรรทัด *ยกเว้น* บรรทัดสุดท้าย (ที่เป็นตัวคั่น)
            motd_lines = lines[:-1]
            message = "\n".join(motd_lines)
            
            return message
            # --- LOGIC ใหม่ จบตรงนี้ ---
            
    except Exception as e:
        return f"Error connecting to {target_ip}: {e}"


# --- (ฟังก์ชัน gigabit_status เหมือนเดิม) ---
def gigabit_status(target_ip):
    device_params = {
        "device_type": "cisco_ios_telnet",
        "ip": target_ip,
        "username": username,
        "password": password,
    }

    ans = "" # String สำหรับแสดงผล
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
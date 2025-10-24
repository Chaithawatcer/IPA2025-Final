from netmiko import ConnectHandler
from pprint import pprint
import re  # <-- 1. Import 're' (Regex) เข้ามา

# TODO: ควรย้ายไปเก็บใน .env
username = "admin"
password = "cisco"

def get_device_params(target_ip):
    """
    Helper function เพื่อสร้าง params ในการเชื่อมต่อ (SSH)
    """
    return {
        "device_type": "cisco_ios",
        "ip": target_ip,
        "username": username,
        "password": password,
    }

# --- ฟังก์ชัน Get MOTD (แก้ไขใหม่ทั้งหมด) ---
def get_motd(target_ip):
    """
    แก้ไข Regex: ให้มองหาตัวคั่น '^C' (2 ตัวอักษร)
    """
    device_params = get_device_params(target_ip)
    try:
        with ConnectHandler(**device_params) as ssh:
            # 1. ดึง config ทั้งหมด
            config_output = ssh.send_command("show running-config")
            
            # 2. --- แก้ไข Regex ---
            # เราจะค้นหา 'banner motd ^C' (โดยต้อง escape \)
            # และจับกลุ่ม (.*?) ที่อยู่ระหว่าง '^C' ทั้งสอง
            
            match = re.search(r'banner motd \^C(.*?)\^C', config_output, re.DOTALL)
            
            if match:
                # ถ้าเจอ, match.group(1) คือข้อความที่เราต้องการ
                message = match.group(1)
                return message.strip() # .strip() เพื่อลบ \n ที่อาจติดมา
            else:
                return "Error: No MOTD Configured"
                
    except Exception as e:
        return f"Error connecting to {target_ip}: {e}"


# --- ฟังก์ชัน gigabit_status (เหมือนเดิม) ---
def gigabit_status(target_ip):
    """
    แก้ไขให้รับ target_ip
    """
    # --- ใช้ params เดิมของคุณ (telnet) ---
    device_params = {
        "device_type": "cisco_ios_telnet",
        "ip": target_ip,
        "username": username,
        "password": password,
    }

    ans = ""
    try:
        with ConnectHandler(**device_params) as ssh:
            up = 0
            down = 0
            admin_down = 0
            result = ssh.send_command("sh int", use_textfsm=True)
            for status in result:
                if status["interface"].startswith("GigabitEthernet"):
                    ans += f"{status['interface']} {status['link_status']}, "
                    if status['link_status'] == "up":
                        up += 1
                    elif status['link_status'] == "down":
                        down += 1
                    elif status['link_status'] == "administratively down":
                        admin_down += 1

            ans = f"{ans[:-2]} -> {up} up, {down} down, {admin_down} administratively down"
            pprint(ans)
            return ans
    except Exception as e:
        return f"Error connecting to {target_ip}: {e}"
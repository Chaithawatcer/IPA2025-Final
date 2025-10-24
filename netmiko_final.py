from netmiko import ConnectHandler
from pprint import pprint

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

# --- ฟังก์ชันใหม่สำหรับ Get MOTD ---
def get_motd(target_ip):
    """
    ใช้ Netmiko + TextFSM (use_textfsm=True)
    เพื่อดึงค่า MOTD จาก 'show running-config'
    """
    device_params = get_device_params(target_ip)
    try:
        with ConnectHandler(**device_params) as ssh:
            # รัน 'show run' และให้ textfsm แปลงผลลัพธ์เป็น structured data (dict)
            result = ssh.send_command("show running-config", use_textfsm=True)
            
            # Template 'cisco_ios_show_running_config' จะเก็บ MOTD ไว้ใน
            # result['banner']['motd']
            if result and isinstance(result, dict) and "banner" in result and "motd" in result["banner"]:
                message = result["banner"]["motd"]
                return message
            else:
                # ถ้าไม่มี key นี้ หรือไม่มี MOTD
                return "Error: No MOTD Configured"
    except Exception as e:
        return f"Error connecting to {target_ip}: {e}"


# --- ฟังก์ชันเดิมที่แก้ไข ---
def gigabit_status(target_ip):
    """
    แก้ไขให้รับ target_ip
    """
    # device_params = get_device_params(target_ip)
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
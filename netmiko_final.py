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

# ---  FIX 1: แก้ไข get_motd ให้เสถียร ---
def get_motd(target_ip):
    """
    ใช้ Netmiko และ 'show banner motd'
    เพื่อดึงค่า MOTD (วิธีนี้เสถียรกว่า 'show run')
    """
    device_params = get_device_params(target_ip)
    try:
        with ConnectHandler(**device_params) as ssh:
            # ใช้ 'show banner motd' จะตรงไปตรงมาและเร็วกว่า
            result = ssh.send_command("show banner motd")
            
            # ผลลัพธ์มี 2 แบบ:
            # 1. ไม่มี: "% No banner configured"
            # 2. มี: "Enter TEXT message. End with the character 'c'.\nHello\nc"
            
            if "% No banner configured" in result:
                return "Error: No MOTD Configured"
            
            # Split ผลลัพธ์เป็นบรรทัด
            lines = result.splitlines()
            
            # ถ้ามีน้อยกว่า 3 บรรทัด (header, body, footer)
            # แสดงว่า MOTD ว่างเปล่า หรือ parse ผิด
            if len(lines) < 3:
                return "Error: No MOTD Configured (empty)"

            # MOTD คือทุกบรรทัด ยกเว้นบรรทัดแรก (header) และบรรทัดสุดท้าย (delimiter)
            motd_lines = lines[1:-1]
            message = "\n".join(motd_lines) # เอามาต่อกัน (เผื่อมีหลายบรรทัด)
            
            return message
            
    except Exception as e:
        return f"Error connecting to {target_ip}: {e}"


# --- FIX 2: แก้ไข gigabit_status ให้แสดงผลเฉพาะ Gi ---
def gigabit_status(target_ip):
    """
    แก้ไขให้รับ target_ip และแก้การแสดงผล string
    """
    # (ใช้ params เดิมของคุณที่เป็น telnet)
    device_params = {
        "device_type": "cisco_ios_telnet",
        "ip": target_ip,
        "username": username,
        "password": password,
    }

    ans = "" # String สำหรับแสดงผล
    try:
        with ConnectHandler(**device_params) as ssh:
            # (ผมเดาว่าคุณเพิ่มตัวแปรนับ Lo มาเอง)
            gi_up, gi_down, gi_admin_down = 0, 0, 0
            lo_up, lo_down, lo_admin_down = 0, 0, 0
            
            result = ssh.send_command("sh int", use_textfsm=True)
            for status in result:
                
                if status["interface"].startswith("GigabitEthernet"):
                    # --- THIS IS THE FIX ---
                    # ต่อ string เฉพาะ interface ที่เป็น Gi เท่านั้น
                    ans += f"{status['interface']} {status['link_status']}, " 
                    # ---
                    
                    if status['link_status'] == "up":
                        gi_up += 1
                    elif status['link_status'] == "down":
                        gi_down += 1
                    elif status['link_status'] == "administratively down":
                        gi_admin_down += 1
                
                elif status["interface"].startswith("Loopback"):
                    # (ส่วนนับ Loopback ของคุณ)
                    if status['link_status'] == "up":
                        lo_up += 1
                    elif status['link_status'] == "down":
                        lo_down += 1
                    elif status['link_status'] == "administratively down":
                        lo_admin_down += 1

            # ลบ (,) ตัวสุดท้ายออก
            if ans:
                ans = ans[:-2] 
            else:
                ans = "No Gigabit Interfaces found"
            
            # (ใช้ format สรุปผลแบบที่คุณทำไว้ใน log)
            ans_summary = f"Gi: {gi_up} up, {gi_down} down, {gi_admin_down} admin-down | Lo: {lo_up} up, {lo_down} down, {lo_admin_down} admin-down"
            
            return f"{ans} -> {ans_summary}"
            
    except Exception as e:
        return f"Error connecting to {target_ip}: {e}"
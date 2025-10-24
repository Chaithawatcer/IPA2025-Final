import subprocess
import json
import os

# TODO: ควรย้ายไปเก็บใน .env เพื่อความปลอดภัย
ANSIBLE_USER = "admin"
ANSIBLE_PASS = "cisco"
ANSIBLE_SSH_ARGS = "-o KexAlgorithms=diffie-hellman-group14-sha1 -o HostKeyAlgorithms=+ssh-rsa"

def _run_ansible_playbook(playbook_name, target_ip, extra_vars=None):
    """
    ฟังก์ชัน Helper สำหรับรัน ansible-playbook แบบ dynamic
    """
    if extra_vars is None:
        extra_vars = {}
    
    # 1. สร้างคำสั่งพื้นฐาน
    # (สำคัญมาก: ต้องมี comma (,) ต่อท้าย target_ip 
    # เพื่อให้ Ansible มองว่าเป็น inventory list)
    command = [
        'ansible-playbook',
        playbook_name,
        '-i', f"{target_ip},",
    ]

    # 2. เตรียมตัวแปรสำหรับ Connection
    base_vars = {
        "ansible_user": ANSIBLE_USER,
        "ansible_password": ANSIBLE_PASS,
        "ansible_ssh_common_args": ANSIBLE_SSH_ARGS
    }
    
    # 3. รวมตัวแปรทั้งหมด (Base + Extra)
    all_vars = {**base_vars, **extra_vars}

    # 4. เพิ่มตัวแปรทั้งหมดลงในคำสั่ง
    command.extend(['-e', json.dumps(all_vars)])
    
    print(f"Running Ansible command: {' '.join(command)}")

    # 5. รันคำสั่ง
    try:
        # เพิ่ม timeout 60 วินาที
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    except Exception as e:
        return {"status": "FAIL", "msg": f"Ansible execution error: {e}", "stdout": ""}
    
    stdout = result.stdout
    stderr = result.stderr
    print("--- Ansible STDOUT ---")
    print(stdout)
    if stderr:
        print("--- Ansible STDERR ---")
        print(stderr)
    print("----------------------")

    # 6. ตรวจสอบผลลัพธ์ (แบบเสถียร)
    # เราจะเช็ค 'recap' แทน 'ok=3' ที่ไม่แน่นอน
    if "failed=0" in stdout and "unreachable=0" in stdout:
         return {"status": "OK", "msg": "Ok: success", "stdout": stdout}
    elif "unreachable=1" in stdout or "Timeout connecting" in stdout:
        return {"status": "FAIL", "msg": f"Error: Ansible cannot connect to {target_ip}", "stdout": stdout}
    else:
        # ถ้ามี failed=1 มันจะเข้า else นี้
        return {"status": "FAIL", "msg": "Error: Ansible playbook failed", "stdout": stdout}

# --- ฟังก์ชันใหม่สำหรับ MOTD ---
def set_motd(target_ip, message):
    """
    เรียกใช้ playbook_motd.yaml เพื่อตั้งค่า MOTD
    """
    extra_vars = {
        "motd_message": message
    }
    return _run_ansible_playbook("playbook_motd.yaml", target_ip, extra_vars)

# --- ฟังก์ชัน showrun ที่แก้ไขใหม่ ---
def showrun(target_ip, student_id):
    """
    เรียกใช้ playbook_showrun.yaml และเช็คว่าไฟล์ถูกสร้างหรือไม่
    """
    extra_vars = {
        "student_id": student_id
    }
    
    run_result = _run_ansible_playbook("playbook_showrun.yaml", target_ip, extra_vars)
    
    if run_result["status"] == "OK":
        # ถ้า playbook รันสำเร็จ, เช็คว่าไฟล์ config ถูกสร้างจริง
        filename = f"backups/show_run_{student_id}_{target_ip}.txt"
        if os.path.exists(filename):
            # คืนค่า "ok" เพื่อให้ ipa2024_final.py รู้ว่าต้องส่งไฟล์
            return {"status": "OK", "msg": "ok"}
        else:
            return {"status": "FAIL", "msg": "Error: Ansible OK, but backup file not found."}
    else:
        # ถ้า Playbook ล้มเหลว ก็ส่ง error กลับไป
        return run_result
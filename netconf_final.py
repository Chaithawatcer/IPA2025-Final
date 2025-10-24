from ncclient import manager
from ncclient.operations.errors import TimeoutExpiredError
from ncclient.transport.errors import SSHError, AuthenticationError
import xml.etree.ElementTree as ET
import os # <-- IMPORT
from dotenv import load_dotenv # <-- IMPORT

load_dotenv() # <-- LOAD .ENV

# --- MODIFIED: Read credentials from .env ---
ROUTER_USERNAME = os.environ.get("ROUTER_USERNAME")
ROUTER_PASSWORD = os.environ.get("ROUTER_PASSWORD")
# (No hardcoded basicauth or studentID needed here)

def get_netconf_params(target_ip):
    """Helper function to build connection parameters."""
    return {
        "host": target_ip,
        "port": 830,
        "username": ROUTER_USERNAME, # <-- Use var from .env
        "password": ROUTER_PASSWORD, # <-- Use var from .env
        "hostkey_verify": False,
        "device_params": {"name": "csr"},
        "timeout": 10
    }

# --- MODIFIED: All functions now accept 'studentID' ---

def create(target_ip, studentID):
    netconf_params = get_netconf_params(target_ip)
    
    # XML Payload for NETCONF
    xml_config = f"""
    <config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
      <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
        <interface>
          <name>Loopback{studentID}</name> 
          <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">ianaift:softwareLoopback</type>
          <enabled>true</enabled>
          <ipv4 xmlns="urn:ietf:params:xml:ns:yang:ietf-ip">
            <address>
              <ip>172.30.30.1</ip>
              <netmask>255.255.255.0</netmask>
            </address>
          </ipv4>
        </interface>
      </interfaces>
    </config>
    """
    
    try:
        with manager.connect(**netconf_params) as m:
            m.edit_config(target='running', config=xml_config, default_operation="merge")
            return f"Interface loopback {studentID} is created successfully (using Netconf)"
    except Exception as e:
        return f"Cannot create: Interface loopback {studentID} (Error: {e}) (using Netconf)"

def delete(target_ip, studentID):
    netconf_params = get_netconf_params(target_ip)
    
    xml_config = f"""
    <config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
      <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
        <interface operation="delete">
          <name>Loopback{studentID}</name>
        </interface>
      </interfaces>
    </config>
    """
    
    try:
        with manager.connect(**netconf_params) as m:
            m.edit_config(target='running', config=xml_config)
            return f"Interface loopback {studentID} is deleted successfully (using Netconf)"
    except Exception as e:
        return f"Cannot delete: Interface loopback {studentID} (Error: {e}) (using Netconf)"

def enable(target_ip, studentID):
    netconf_params = get_netconf_params(target_ip)
    
    xml_config = f"""
    <config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
      <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
        <interface>
          <name>Loopback{studentID}</name>
          <enabled>true</enabled>
        </interface>
      </interfaces>
    </config>
    """
    
    try:
        with manager.connect(**netconf_params) as m:
            m.edit_config(target='running', config=xml_config, default_operation="merge")
            return f"Interface loopback {studentID} is enabled successfully (using Netconf)"
    except Exception as e:
        return f"Cannot enable: Interface loopback {studentID} (Error: {e}) (using Netconf)"

def disable(target_ip, studentID):
    netconf_params = get_netconf_params(target_ip)
    
    xml_config = f"""
    <config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
      <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
        <interface>
          <name>Loopback{studentID}</name>
          <enabled>false</enabled>
        </interface>
      </interfaces>
    </config>
    """
    
    try:
        with manager.connect(**netconf_params) as m:
            m.edit_config(target='running', config=xml_config, default_operation="merge")
            return f"Interface loopback {studentID} is shutdowned successfully (using Netconf)"
    except Exception as e:
        return f"Cannot shutdown: Interface loopback {studentID} (Error: {e}) (using Netconf)"

def status(target_ip, studentID):
    netconf_params = get_netconf_params(target_ip)
    
    xml_filter = f"""
    <filter type="subtree">
      <interfaces-state xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
        <interface>
          <name>Loopback{studentID}</name>
          <oper-status/>
          <admin-status/>
        </interface>
      </interfaces-state>
    </filter>
    """
    
    try:
        with manager.connect(**netconf_params) as m:
            data_xml = m.get(filter=xml_filter)
            
            root = ET.fromstring(str(data_xml))
            data_element = root.find('{urn:ietf:params:xml:ns:netconf:base:1.0}data')
            
            if data_element is None:
                 return f"No Interface loopback {studentID} (checked by Netconf)"
                 
            ns = {'if': 'urn:ietf:params:xml:ns:yang:ietf-interfaces'}
            interface = data_element.find(f'.//if:interface[if:name="Loopback{studentID}"]', ns)
            
            if interface is None:
                return f"No Interface loopback {studentID} (checked by Netconf)"

            admin_status_elem = interface.find('if:admin-status', ns)
            oper_status_elem = interface.find('if:oper-status', ns)

            if admin_status_elem is not None and oper_status_elem is not None:
                admin_status = admin_status_elem.text
                oper_status = oper_status_elem.text
                
                if admin_status == 'up' and oper_status == 'up':
                    return f"Interface loopback {studentID} is enabled (checked by Netconf)"
                else:
                    return f"Interface loopback {studentID} is disabled (checked by Netconf)"
            else:
                return f"No Interface loopback {studentID} (checked by Netconf)"

    except (SSHError, AuthenticationError, TimeoutExpiredError) as e:
        return f"Cannot connect to {target_ip}: {e} (checked by Netconf)"
    except Exception as e:
        return f"Undefined Error (Error: {e}) (checked by Netconf)"
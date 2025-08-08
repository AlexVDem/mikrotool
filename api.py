#!/usr/bin/python3
import sys
import pprint
import os
sys.path.append(os.getcwd())
import routeros_api
import json

base_dir = os.path.dirname(os.path.abspath(__file__))
conf_path = os.path.join(base_dir, 'api.conf')

def helpcomline():
    print("\nUsage: python3 /home/user/miktool/api.py OPTIONS [Router] [Mangle]\n\nOPTIONS: c [onfig] will show api.conf config with all settings,\n         r [outer config] will show api.conf for specific router, works only with [Router] name from api.conf,\n         sw [itch] ON/OFF mangle rules, works only with [Router] name and [Mangle] rule name from api.conf\nExample: python3 /home/user/miktool/api.py sw Mikrotik0 'VPN for User1'\n(will switch mangle with 'VPN for User1' name ON or OFF on Mikrotik0 router)")
    sys.exit(0)

def jsonpart(json_object, name):
    for mikrotik_data in json_object:
        if mikrotik_data.get("mikrotikname") == name:
            found_mikrotik = mikrotik_data
            return (json.dumps(found_mikrotik))

def openconf(keyarg):
    try:
        with open(conf_path, 'r') as f:
            try:
                config = json.load(f)
            except ValueError as e:
                print("Error: Unable to decode JSON, Error: {}. Manually verify JSON output.".format(e))
            else:
                if keyarg[1] == "c":
                    return(json.dumps(config))
                if (keyarg[1] == "r" or keyarg[1] == "sw" or keyarg[1] == "st") and keyarg[2] is not None:
                    values = jsonpart(config, keyarg[2])
                    if values is not None:
                        return(values)
                    else:
                        print(f"There is no '{keyarg[2]}' in api.conf file.")
                        sys.exit(1)
    except FileNotFoundError:
        print("Config file was not found.")
    except IOError:
        print("An error occurred while reading config file.")
    
def switchman(swarg):
    try:
        config = json.loads(openconf(swarg))
    except ValueError as e:
        print("Error: Unable to decode JSON, Error: {}. Manually verify JSON output.".format(e))
    else:
        HOST = config["data"]["host"]
        USERNAME = config["data"]["username"]
        PASSWORD = config["data"]["password"]
        API_PORT = config["data"]["apiport"]
        USE_SSL = config["data"]["usessl"]
        MANGLE_RULE_COMMENT = swarg[3] 
    connection = None
    try:
        print(f"Connecting to MikroTik device at {HOST}:{API_PORT}...")
        connection = routeros_api.RouterOsApiPool(
            host=HOST,
            username=USERNAME,
            password=PASSWORD,
            port=API_PORT,
            plaintext_login=True,
            use_ssl=USE_SSL
        )
        api = connection.get_api()
        print("Connection successful.")
        # Access the mangle resource
        mangle = api.get_resource('/ip/firewall/mangle')
        # Find the rule by its comment
        print(f"Searching for mangle rule with comment: '{MANGLE_RULE_COMMENT}'...")
        rules = mangle.get(comment=MANGLE_RULE_COMMENT)
        
        if rules and swarg[1] == "st":
            rule_dis = rules[0]['disabled']
            print("and now...")
            sys.exit(rule_dis)

        if rules:
            # A list of dictionaries is returned; we'll work with the first one.
            rule_data = rules[0]
            # We'll explicitly check for the 'id' key to provide a more specific error
            if 'id' in rule_data:
                rule_id = rule_data['id']
                rule_dis = rule_data['disabled']
                print(f"Found rule with ID: {rule_id}")
            
                if len (sys.argv) > 1 and sys.argv[1] == "sw":
                    # ON/OFF the found rule
                    if rule_dis == "true":
                        print("Enabling the rule...")
                        mangle.set(id=rule_id, disabled='no')
                        print("Mangle rule enabled successfully.")
                    else:
                        print("Disabling the rule...")
                        mangle.set(id=rule_id, disabled='yes')
                        print("Mangle rule disabled successfully.")
                else:
                    print(f"Rule: {rule_data}")
            else:
                print("Error: The found rule does not have a valid '.id' key.", file=sys.stderr)
                print("Full rule data for debugging:", file=sys.stderr)
                pprint.pprint(rule_data, stream=sys.stderr)
                sys.exit(1)
        else:
            print(f"Error: Rule with comment '{MANGLE_RULE_COMMENT}' not found on the device.", file=sys.stderr)
            sys.exit(1)

    except routeros_api.exceptions.RouterOsApiError as e:
        print(f"An API error occurred: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        # Ensure the connection is always closed
        if connection:
            print("Disconnecting from MikroTik")
            connection.disconnect()
    
if len (sys.argv) <2:
    helpcomline()

if len (sys.argv) >1 and sys.argv[1] == "c":    
    print(f"{openconf(sys.argv)}")

if len (sys.argv) >2 and sys.argv[1] == "r":
    print(f"{openconf(sys.argv)}")

if len (sys.argv) >3 and sys.argv[1] == "sw":
    switchman(sys.argv)

if len (sys.argv) >3 and sys.argv[1] == "st":
    switchman(sys.argv)
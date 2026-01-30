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
    print("\nUsage: python3 /home/user/miktool/api.py OPTIONS [Router] [Mangle]\n\nOPTIONS: c[onfig] will show api.conf config with all settings,\n         r[outer config] will show api.conf for specific router, works only with [Router] name from api.conf,\n         sw[itch] ON/OFF mangle rules, works only with [Router] name and [Mangle] rule name from api.conf\nExample: python3 /home/user/miktool/api.py sw Mikrotik0 'VPN for User1' (will switch mangle with 'VPN for User1' name ON or OFF on Mikrotik0 router)")
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
        print("Error: Unable to decode JSON, Error: {}. Manually verify JSON output.".format(e), file=sys.stderr)
    else:
        #print(config)
        HOST = config["data"]["host"]
        USERNAME = config["data"]["username"]
        PASSWORD = config["data"]["password"]
        API_PORT = config["data"]["apiport"]
        USE_SSL = config["data"]["usessl"]
        MANGLE_RULE_COMMENT = swarg[3] if len(swarg) > 3 else None
    connection = None
    try:
        print(f"Connecting to MikroTik device at {HOST}:{API_PORT}...", file=sys.stderr)
        connection = routeros_api.RouterOsApiPool(
            host=HOST,
            username=USERNAME,
            password=PASSWORD,
            port=API_PORT,
            plaintext_login=True,
            use_ssl=USE_SSL
        )
        api = connection.get_api()
        print("Connection successful.", file=sys.stderr)
        # Access the mangle resource with proper boolean handling
        mangle_structure = routeros_api.api_structure.default_structure.copy()
        mangle_structure['disabled'] = routeros_api.api_structure.BooleanField()
        mangle = api.get_resource('/ip/firewall/mangle', structure=mangle_structure)

        if swarg[1] == "st" and MANGLE_RULE_COMMENT is None:
            all_rules = mangle.get()
            target_comments = config.get("rulecomments", {}).values()
            device_rules_map = {r.get('comment'): r.get('disabled') for r in all_rules if 'comment' in r}
            status_map = {}
            for comment in target_comments:
                if comment in device_rules_map:
                    status_map[comment] = device_rules_map[comment]
            print(json.dumps(status_map))
            sys.exit(0)

        if MANGLE_RULE_COMMENT is None:
             print("Error: Mangle rule comment is required for this command.", file=sys.stderr)
             sys.exit(1)

        # Find the rule by its comment
        print(f"Searching for mangle rule with comment: '{MANGLE_RULE_COMMENT}'...", file=sys.stderr)
        rules = mangle.get(comment=MANGLE_RULE_COMMENT)
        
        if rules and swarg[1] == "st":
            rule_dis = rules[0]['disabled']
            print(json.dumps(rule_dis))
            sys.exit(0)

        if rules:
            # A list of dictionaries is returned; we'll work with the first one.
            rule_data = rules[0]
            # We'll explicitly check for the 'id' key to provide a more specific error
            if 'id' in rule_data:
                rule_id = rule_data['id']
                rule_dis = rule_data['disabled']
                print(f"Found rule with ID: {rule_id}", file=sys.stderr)
                #print(f"Rule: {rule_data}")
            
                if len (sys.argv) > 1 and sys.argv[1] == "sw":
                    # ON/OFF the found rule
                    if rule_dis: # If rule is disabled (True)
                        print("Enabling the rule...", file=sys.stderr)
                        mangle.set(id=rule_id, disabled=False)
                        print("Mangle rule enabled successfully.", file=sys.stderr)
                    else:
                        print("Disabling the rule...", file=sys.stderr)
                        mangle.set(id=rule_id, disabled=True)
                        print("Mangle rule disabled successfully.", file=sys.stderr)
                else:
                    print(f"Rule: {rule_data}", file=sys.stderr)
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
            print("Disconnecting from MikroTik", file=sys.stderr)
            connection.disconnect()
        # return mangle condition
        #sys.exit(rule_dis)
        #sys.exit(0)
    
if len (sys.argv) <2:
    helpcomline()

if len (sys.argv) >1 and sys.argv[1] == "c":    
    print(f"{openconf(sys.argv)}")

if len (sys.argv) >2 and sys.argv[1] == "r":
    print(f"{openconf(sys.argv)}")

if len (sys.argv) >3 and sys.argv[1] == "sw":
    switchman(sys.argv)

if len (sys.argv) >2 and sys.argv[1] == "st":
    switchman(sys.argv)
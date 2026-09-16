import worldmonitor_sdk
import json

def main():
    client = worldmonitor_sdk.Client()
    print("Fetching tools list via SDK...")
    try:
        tools = client.list_tools()
        print(f"Found {len(tools.get('tools', []))} tools.")
        if tools.get('tools'):
            print("First tool name:", tools['tools'][0]['name'])
    except Exception as e:
        print(f"Error fetching tools: {e}")

if __name__ == '__main__':
    main()

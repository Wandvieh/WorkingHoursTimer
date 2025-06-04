import json

# testing what json.load outputs
CONFIG_FILE = "config.json"
with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)
    print(data)
import json

with open('tools.jsonl', 'r') as json_file:
    json_list = list(json_file)

print(json_list[1]['type'])






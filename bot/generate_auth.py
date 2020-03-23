import csv
import json
import secrets
import string
from sys import argv

alphabet = string.ascii_letters + string.digits

filename = argv[1]
output_dict = {
    "authentication": []
}
output_csv = []
with open(filename, 'r') as f:
    f.readline()
    reader = csv.reader(f)
    for name, email in reader:
        key = ''.join(secrets.choice(alphabet) for i in range(16))
        output_csv.append([name, email, key])
        output_dict["authentication"].append({
            "name": name,
            "key": key
        })

with open("mail202.csv", 'w') as f:
    for row in output_csv:
        f.write(','.join(row) + '\n')

print(json.dumps(output_dict, indent=2))

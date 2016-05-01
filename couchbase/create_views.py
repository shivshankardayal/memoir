import os

os.system('curl -X PUT -H "Content-Type: application/json" -u shiv:Augustya25$ http://localhost:8092/memoir/_design/dev_users -d @default.json')
os.system('curl -X PUT -H "Content-Type: application/json" -u shiv:Augustya25$ http://localhost:8092/memoir/_design/dev_questions -d @questions.json')
os.system('curl -X PUT -H "Content-Type: application/json" -u shiv:Augustya25$ http://localhost:8092/memoir/_design/dev_polls -d @polls.json')
os.system('curl -X PUT -H "Content-Type: application/json" -u shiv:Augustya25$ http://localhost:8092/memoir/_design/dev_kunjika -d @kunjika.json')
os.system('curl -X PUT -H "Content-Type: application/json" -u shiv:Augustya25$ http://localhost:8092/memoir/_design/dev_tags -d @tags.json')

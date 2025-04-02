from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

origins = [
    "http://localhost:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
class Server(BaseModel):
    name: str
    address: str
    port: int
    type: str

def remove_server_from_config(server_name: str):
    haproxy_config_path = '/etc/haproxy/haproxy.cfg'
    
    with open(haproxy_config_path, 'r') as file:
        lines = file.readlines()
    
    new_lines = []
    for line in lines:
        if not (line.strip().startswith('server') and server_name in line):
            new_lines.append(line)
    
    with open(haproxy_config_path, 'w') as file:
        file.writelines(new_lines)

def add_server_to_backend(backend: str, server: Server):
    haproxy_config_path = '/etc/haproxy/haproxy.cfg'

    with open(haproxy_config_path, 'r') as file:
        lines = file.readlines()

    backend_found = False
    server_line = f"    server {server.name} {server.address}:{server.port} check"
    if backend != "mysql_servers":
        server_line += f" cookie {server.name}"

    for i, line in enumerate(lines):
        if line.strip() == f'backend {backend}':
            backend_found = True
            while i + 1 < len(lines) and not lines[i + 1].startswith('    server'):
                i += 1

            lines.insert(i + 1, server_line + '\n')

            break

    if not backend_found:
        lines.append(f'\nbackend {backend}\n')
        lines.append(server_line + '\n')

    with open(haproxy_config_path, 'w') as file:
        file.writelines(lines)

def list_servers():
    haproxy_config_path = '/etc/haproxy/haproxy.cfg'
    servers = {"backends": [], "db_servers": []}

    with open(haproxy_config_path, 'r') as file:
        lines = file.readlines()

    current_backend = None
    for line in lines:
        line = line.strip()

        if line.startswith('backend'):
            current_backend = line.split()[1]  # Le nom du backend
        elif line.startswith('server') and current_backend:
            server_details = line.split()
            server_name = server_details[1]
            server_address, server_port = server_details[2].split(":")

            server_info = {"name": server_name, "address": server_address, "port": int(server_port)}
            if current_backend == "backend":
                servers["backends"].append(server_info)
            elif current_backend == "mysql_servers":
                servers["db_servers"].append(server_info)

    return servers

@app.post("/haproxy/add_app_server")
def add_app_server(server: Server):
    add_server_to_backend("backend", server)
    return {"message": f"Serveur {server.name} ajouté à la configuration des serveurs de l'application."}

@app.post("/haproxy/add_db_server")
def add_db_server(server: Server):
    add_server_to_backend("mysql_servers", server)
    return {"message": f"Serveur {server.name} ajouté à la configuration des serveurs de base de données."}

@app.delete("/haproxy/remove_server/{server_name}")
def remove_server(server_name: str):
    try:
        remove_server_from_config(server_name)
        return {"message": f"Serveur {server_name} supprimé de la configuration."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la suppression du serveur: {e}")

@app.get("/haproxy/config")
def get_haproxy_config():
    haproxy_config_path = '/etc/haproxy/haproxy.cfg'
    try:
        with open(haproxy_config_path, 'r') as file:
            return {"config": file.read()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la lecture de la configuration: {e}")

@app.get("/haproxy/list_servers")
def list_all_servers():
    try:
        servers = list_servers()
        return servers
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la lecture des serveurs: {e}")

# Endpoint pour redémarrer HAProxy (commenté)
# @app.post("/haproxy/restart")
# def restart_haproxy():
#     try:
#         os.system('systemctl restart haproxy')  # Redémarrer HAProxy
#         return {"message": "HAProxy a été redémarré avec succès."}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Erreur lors du redémarrage de HAProxy: {e}")

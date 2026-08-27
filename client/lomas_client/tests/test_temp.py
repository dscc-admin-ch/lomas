# from pathlib import Path
# from fastapi.testclient import TestClient
# from lomas_server.app import get_admin_app
# from lomas_server.models.config import Config

# config = Config()
# config.database.wipe()
# config.database.set_bootstrap(config.bootstrap)

# with TestClient(get_admin_app(config), headers={"Authorization": f"Bearer {config.bootstrap}"}) as client:
#     breakpoint()
#     response = client.post("/backup")
#     print(response.status_code, response.json())

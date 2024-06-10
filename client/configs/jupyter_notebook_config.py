# type: ignore
from jupyter_server.auth import passwd

c = get_config()  # noqa: F821

password: str = "dprocks"
c.NotebookApp.password = passwd(password)

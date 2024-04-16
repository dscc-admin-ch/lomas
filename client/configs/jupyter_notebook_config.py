from jupyter_server.auth import passwd

c = get_config()  # noqa

password: str = "dprocks"
c.NotebookApp.password = passwd(password)

# Tips for developers

## Start service
### On local machine
To start the container on a local machine, go to `lomas/server/` and run `docker compose up`. 
If you encounter any issue, you might want to run `docker compose down` first.

### On a kubernetes cluser
-- TODO: can someone fill it: like as few lines as possible

### On Onyxia
To start the server on Onyxia, select the `lomas `service, (optionnally adapt the administration and runtime parameters) et click on 'Lancer'.

## Tests
It is possible to test the server within and outside the docker container.

### On local machine
The tests will be based on the config in `lomas/server/src/tests/test_config` and be executed with the AdminYamlDatabase. 
Therefore, go to `lomas/server/src` and run `python -m unittest discover -s .`

### In container
The tests will be based on the config in `lomas/server/src/tests/test_config` and be executed with the AdminMongoDatabase. For this, go to `lomas/server/src` and run `python -m unittest discover -s .`

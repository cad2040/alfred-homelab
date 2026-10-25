#domain:docker-ufw

MySQL from a Compose stack is reachable on the LAN even though UFW denies 3306.
Explain the correct fix using DOCKER-USER (not `ufw allow`). Mention binding
databases to 127.0.0.1 when they should not be LAN-published.

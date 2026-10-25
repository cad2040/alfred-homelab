---
name: docker-ufw
description: >-
  Docker publishes vs UFW: DOCKER-USER LAN then DROP; compose hostPort:containerPort
  (not CIDR in ports); bind inference/DB to 127.0.0.1; no 0.0.0.0 MySQL.
primary_domain: docker-ufw
domains: [docker-ufw]
routing_tags: ["#domain:docker-ufw"]
preferred_model: alfred-coder
---

# Docker + UFW
#domain: docker-ufw

## Hard rules

1. UFW does **not** gate Docker publishes — use **iptables `DOCKER-USER`**, never bare `ufw allow` as Docker control.
2. LAN ports: RELATED/ESTABLISHED RETURN → your LAN CIDR RETURN → DROP; persist with `netfilter-persistent` (or your distro equivalent).
3. Compose publish = `"HOST:CONTAINER"` — **never** `"CIDR:HOST:CONTAINER"`. LAN filter is DOCKER-USER.
4. Ollama / Chroma / similar inference stores → **`127.0.0.1`** publishes unless you have an explicit LAN plan.
5. Never publish MySQL/Postgres on `0.0.0.0` “for convenience.”

## Template

```bash
# Replace 192.168.1.0/24 and ports with YOUR lab.
sudo iptables -N DOCKER-USER 2>/dev/null || true
sudo iptables -I DOCKER-USER 1 -m conntrack --ctstate RELATED,ESTABLISHED -j RETURN
sudo iptables -I DOCKER-USER 2 -s 192.168.1.0/24 -p tcp -m multiport --dports 3000,4000 -j RETURN
sudo iptables -I DOCKER-USER 3 -p tcp -m multiport --dports 3000,4000 -j DROP
sudo netfilter-persistent save
```

```yaml
# ui:     "3000:3000"              # DOCKER-USER filters LAN
# litellm:"127.0.0.1:4000:4000"
# ollama: "127.0.0.1:11434:11434"
# chroma: "127.0.0.1:8000:8000"
```

## Never

`ufw allow` as Docker control; DROP before LAN RETURN; CIDR inside `ports:`; Ollama/Chroma on `0.0.0.0` without a firewall story.

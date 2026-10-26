---
name: docker-ufw
description: >-
  Docker publishes vs UFW: DOCKER-USER LAN then DROP; compose hostPort:containerPort
  (not CIDR in ports); Ollama/LiteLLM 127.0.0.1; no 0.0.0.0 MySQL.
source_repo: cad2040/alfred-homelab
source_path: skills/docker-ufw
primary_domain: docker-ufw
domains: [docker-ufw]
routing_tags: ["#domain:docker-ufw"]
preferred_model: alfred-coder
---

# Docker + UFW (lab LAN)
#domain: docker-ufw

## Rules
1. UFW does **not** gate Docker publishes — use **iptables `DOCKER-USER`**, never bare `ufw allow`.
2. LAN ports: RELATED/ESTABLISHED RETURN → `YOUR_LAN_CIDR` RETURN → DROP; `netfilter-persistent save`.
3. Compose publish = `"HOST:CONTAINER"` (e.g. `"8080:8080"`) — **never** `"YOUR_LAN_CIDR:8080:8080"`. LAN filter is DOCKER-USER.
4. Ollama / LiteLLM / Chroma on **`127.0.0.1`** until you understand DOCKER-USER — never casual `0.0.0.0`.
5. Never publish MySQL on `0.0.0.0`.

## Template

```bash
# Replace YOUR_LAN_CIDR (e.g. 192.168.1.0/24) before applying.
sudo iptables -N DOCKER-USER 2>/dev/null || true
sudo iptables -I DOCKER-USER 1 -m conntrack --ctstate RELATED,ESTABLISHED -j RETURN
sudo iptables -I DOCKER-USER 2 -s YOUR_LAN_CIDR -p tcp -m multiport --dports 3000,4000 -j RETURN
sudo iptables -I DOCKER-USER 3 -p tcp -m multiport --dports 3000,4000 -j DROP
sudo netfilter-persistent save
```

```yaml
# litellm:  "127.0.0.1:4000:4000"
# ollama:   "127.0.0.1:11434:11434"
# new_svc:  "8080:8080"   # DOCKER-USER filters LAN — NOT "CIDR:8080:8080"
```

## Never
`ufw allow` as Docker control; DROP before LAN RETURN; CIDR inside `ports:`; inference on `0.0.0.0` without a firewall story.

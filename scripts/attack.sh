#!/bin/bash
# A fast script to trigger real eBPF signatures

# 1. Trigger /etc/shadow read alert
cat /etc/shadow > /dev/null 2>&1

# 2. Trigger Docker sock access alert
cat /var/run/docker.sock > /dev/null 2>&1

# 3. Trigger suspicious shell (netcat/bash) alert
nc -z localhost 8080 > /dev/null 2>&1
bash -c "echo 'stealth shell'" > /dev/null 2>&1

echo "Attack executed on host at $(date)" >> data/attack_log.txt
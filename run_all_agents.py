# run_all_px4_agents.py
# To run it: uv run python3 run_all_agents.py

import subprocess

# List of agent modules to launch using -m
AGENT_MODULES = [
    "agents.greeting_agent",
    "agents.tell_time_agent",
    "agents.px4_search_agent",
    "agents.px4_summarizer_agent",
    "agents.px4_command_agent"
    
]

# Start each agent module in a subprocess
processes = []
for module in AGENT_MODULES:
    cmd = f"python -m {module}"
    print(f"[LAUNCHING] {cmd}")
    p = subprocess.Popen(cmd, shell=True)
    processes.append(p)

# Optional: Wait for all to finish (blocks the terminal)
for p in processes:
    p.wait()

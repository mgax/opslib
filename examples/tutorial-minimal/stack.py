from pathlib import Path

from opslib import LocalHost, Stack

COMPOSE_YML = """\
version: "3"
services:
  app:
    image: gitea/gitea:1.19.0
    volumes:
      - ./data:/data
    restart: unless-stopped
    ports:
      - 127.0.0.1:3000:3000
"""

stack = Stack(__name__)
stack.host = LocalHost()
stack.directory = stack.host.directory(Path(__file__).parent / "target")

stack.compose_file = stack.directory.file(
    name="docker-compose.yml",
    content=COMPOSE_YML,
)

stack.compose_up = stack.directory.command(
    args=["docker", "compose", "up", "-d"],
)

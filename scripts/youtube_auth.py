"""Ручной вход в YouTube MCP: печатает ссылку, браузер не открывает (WSL).
Запуск: ~/.local/share/uv/tools/youtube-studio-mcp/bin/python scripts/youtube_auth.py
Ссылку открыть в браузере Windows; после согласия токен сохранится в ~/.youtube-mcp/token.json."""
from google_auth_oauthlib.flow import InstalledAppFlow
from youtube_mcp.auth import SCOPES, YouTubeAuth

a = YouTubeAuth()
flow = InstalledAppFlow.from_client_secrets_file(str(a.client_secret_path), SCOPES)
a._save_token(flow.run_local_server(port=8765, open_browser=False, timeout_seconds=600))
print("OK, токен сохранён:", a.token_path)

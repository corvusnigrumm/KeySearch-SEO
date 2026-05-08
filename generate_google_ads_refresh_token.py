"""
Genera un refresh token de Google Ads usando un archivo OAuth descargado
desde Google Cloud Console.

Soporta clientes OAuth de tipo "installed" y "web". Para "web", el redirect
URI local debe estar autorizado previamente en Google Cloud.
"""
from __future__ import annotations

import argparse
import json
import secrets
import socketserver
import sys
import threading
import urllib.parse
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler
from pathlib import Path

import requests


ADS_SCOPE = "https://www.googleapis.com/auth/adwords"


@dataclass
class OAuthClient:
    client_id: str
    client_secret: str
    auth_uri: str
    token_uri: str
    client_type: str


class _CallbackServer(socketserver.TCPServer):
    allow_reuse_address = True

    def __init__(self, server_address, request_handler_class):
        super().__init__(server_address, request_handler_class)
        self.query_params = None


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        self.server.query_params = query

        if "code" in query:
            message = (
                "<html><body><h2>Autorizacion completada.</h2>"
                "<p>Vuelve a la consola; ya puedes cerrar esta pestana.</p></body></html>"
            )
        else:
            message = (
                "<html><body><h2>No se pudo obtener el codigo.</h2>"
                "<p>Revisa la consola para ver el detalle.</p></body></html>"
            )

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(message.encode("utf-8"))

    def log_message(self, format, *args):
        return


def _load_oauth_client(path: Path) -> OAuthClient:
    data = json.loads(path.read_text(encoding="utf-8"))

    if "installed" in data:
        payload = data["installed"]
        client_type = "installed"
    elif "web" in data:
        payload = data["web"]
        client_type = "web"
    else:
        raise ValueError("El JSON no contiene una seccion 'installed' ni 'web'.")

    return OAuthClient(
        client_id=payload["client_id"],
        client_secret=payload["client_secret"],
        auth_uri=payload["auth_uri"],
        token_uri=payload["token_uri"],
        client_type=client_type,
    )


def _build_authorization_url(client: OAuthClient, redirect_uri: str, state: str) -> str:
    params = {
        "client_id": client.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": ADS_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{client.auth_uri}?{urllib.parse.urlencode(params)}"


def _exchange_code_for_tokens(
    client: OAuthClient,
    code: str,
    redirect_uri: str,
) -> dict:
    response = requests.post(
        client.token_uri,
        data={
            "client_id": client.client_id,
            "client_secret": client.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Genera un refresh token para Google Ads usando OAuth local."
    )
    parser.add_argument(
        "--oauth-client-file",
        required=True,
        help="Ruta al JSON descargado desde Google Cloud Console.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Puerto local para recibir el callback de OAuth. Por defecto: 8080.",
    )
    parser.add_argument(
        "--no-open-browser",
        action="store_true",
        help="No intenta abrir el navegador; solo imprime la URL.",
    )
    args = parser.parse_args()

    oauth_file = Path(args.oauth_client_file)
    if not oauth_file.exists():
        print(f"No existe el archivo: {oauth_file}", file=sys.stderr)
        return 1

    client = _load_oauth_client(oauth_file)
    redirect_uri = f"http://127.0.0.1:{args.port}"
    state = secrets.token_urlsafe(24)

    server = _CallbackServer(("127.0.0.1", args.port), _CallbackHandler)
    server_thread = threading.Thread(target=server.handle_request, daemon=True)
    server_thread.start()

    authorization_url = _build_authorization_url(client, redirect_uri, state)

    print("\nAbre esta URL con la cuenta que usas en Google Ads:\n")
    print(authorization_url)
    print(f"\nEsperando callback en {redirect_uri} ...")

    if not args.no_open_browser:
        webbrowser.open(authorization_url)

    server_thread.join()

    query = server.query_params or {}

    if "error" in query:
        print(f"\nGoogle devolvio un error: {query['error'][0]}", file=sys.stderr)
        return 1

    if query.get("state", [None])[0] != state:
        print("\nEl estado recibido no coincide. Se cancela por seguridad.", file=sys.stderr)
        return 1

    code = query.get("code", [None])[0]
    if not code:
        print("\nNo se recibio el codigo de autorizacion.", file=sys.stderr)
        return 1

    try:
        token_data = _exchange_code_for_tokens(client, code, redirect_uri)
    except requests.HTTPError as exc:
        print("\nError al intercambiar el codigo por tokens.", file=sys.stderr)
        print(exc.response.text, file=sys.stderr)
        return 1

    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        print(
            "\nNo llego refresh_token. Repite el flujo y asegurate de aceptar permisos con prompt de consentimiento.",
            file=sys.stderr,
        )
        return 1

    print("\nRefresh token generado correctamente:\n")
    print(refresh_token)
    print("\nCopia estos valores a tu archivo google-ads.yaml:\n")
    print(f'client_id: "{client.client_id}"')
    print(f'client_secret: "{client.client_secret}"')
    print(f'refresh_token: "{refresh_token}"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

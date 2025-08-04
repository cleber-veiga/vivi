import os
from settings import settings
from pyngrok import ngrok

def get_public_base_url() -> str:
    if getattr(settings, "USE_NGROK", False):
        if os.getenv("NGROK_TUNNEL_OPENED") and os.getenv("NGROK_PUBLIC_URL"):
            return os.environ["NGROK_PUBLIC_URL"]

        # fallback defensivo (caso seja o primeiro a chamar e ainda não tenha tunnel)
        port = int(settings.SERVER_PORT)
        ngrok.set_auth_token(settings.NGROK_AUTH_TOKEN)
        tunnel = ngrok.connect(port, proto="http")
        os.environ["NGROK_TUNNEL_OPENED"] = "1"
        os.environ["NGROK_PUBLIC_URL"] = tunnel.public_url
        print(f"🔥 API disponível em (fallback): {tunnel.public_url}")
        return tunnel.public_url
    else:
        return settings.URL_APPLICATION

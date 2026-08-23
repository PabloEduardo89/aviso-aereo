import os
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("INSTAGRAM_TOKEN")

if not token:
    print("❌ Token não encontrado no .env. Confira o nome da variável (INSTAGRAM_TOKEN).")
else:
    url = "https://graph.facebook.com/v21.0/me/accounts"
    params = {"access_token": token}
    response = requests.get(url, params=params)
    data = response.json()

    if response.status_code == 200 and "data" in data:
        print("✅ Token válido! Páginas encontradas:")
        for page in data["data"]:
            print(f"  - {page['name']} (ID: {page['id']})")
    else:
        print("❌ Erro ao validar o token:")
        print(data)
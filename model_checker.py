import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq()

try:
  models = client.models.list()
  print("利用可能なモデル一覧:")
  for model in models.data:
    print(f"- {model.id}")
except Exception as e:
  print(f"エラーが発生しました: {e}")
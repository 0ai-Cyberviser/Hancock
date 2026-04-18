import os
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

def github_models_chat(prompt: str, model: str = "meta/Llama-4-Maverick-17B-128E-Instruct-FP8", max_tokens: int = 2000) -> str:
    """GitHub Models backend (free tier + paid fallback)"""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("Set GITHUB_TOKEN env var")
    
    client = ChatCompletionsClient(
        endpoint="https://models.github.ai/inference",
        credential=AzureKeyCredential(token),
    )
    
    response = client.complete(
        messages=[SystemMessage("You are Hancock, elite cybersecurity specialist by CyberViser."), UserMessage(prompt)],
        temperature=0.7,
        max_tokens=max_tokens,
        model=model
    )
    return response.choices[0].message.content

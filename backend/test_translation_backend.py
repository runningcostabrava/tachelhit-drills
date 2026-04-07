import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from main import translate_with_hf

async def test():
    print("Testing Translation...")
    text = "Hola, com estàs?"
    src = "Catalan"
    tgt = "Tachelhit/Central Atlas Tamazight"
    print(f"Translating: '{text}' from {src} to {tgt}")
    
    # We run it synchronously as it is defined in main.py, but using asyncio.to_thread just like the endpoint
    try:
        translation = await asyncio.to_thread(translate_with_hf, text, src, tgt)
        print(f"Result: {translation}")
    except Exception as e:
        print(f"Exception caught: {e}")

if __name__ == "__main__":
    asyncio.run(test())

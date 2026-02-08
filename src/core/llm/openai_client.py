from openai import AsyncOpenAI

class OpenAIClient:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(
            api_key=api_key,
            timeout=120.0,
        )
    
    async def generate(self, prompt: str, model: str = "gpt-4o-mini") -> str:
        response = await self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        if not response.choices:
            raise ValueError("No response from OpenAI API")
        return response.choices[0].message.content

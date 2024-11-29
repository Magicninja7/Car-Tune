import anthropic
import os

api_key = os.getenv("ANTHROPIC_API_KEY")
if api_key is None:
    raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

client = anthropic.Anthropic(api_key=api_key)

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1000,
    temperature=0,
    system="You are a world-class poet. Respond only with short poems.",
    messages=[
        {
            "role": "user", 
            "content": [{"type": "text", "text": "Why is the ocean salty?"}]
        }
    ]
)

# Get and print the poem
poem = message.content[0].text
print(poem)

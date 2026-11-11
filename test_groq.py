import os
from groq import Groq

api_key = os.environ.get("GROQ_API_KEY")

if not api_key:
    print("ERROR: GROQ_API_KEY is not configured.")
    raise SystemExit(1)

print("GROQ_API_KEY detected.")

client = Groq(api_key=api_key)

print("Sending test request to Groq...")

response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[
        {
            "role": "system",
            "content": "You are a helpful meeting assistant."
        },
        {
            "role": "user",
            "content": "In one short sentence, explain what a DevOps engineer does."
        }
    ],
    max_completion_tokens=100,
)

answer = response.choices[0].message.content

print()
print("Groq response:")
print(answer)
print()
print("Groq test completed successfully.")
from openai import OpenAI

client = OpenAI(
    base_url='http://localhost:11434/v1/',
    api_key='ollama',  # required but ignored
)

chat_completion = client.chat.completions.create(
    messages=[
        {
            'role': 'user',
            'content': 'Why you create this project?',
        }
    ],
    model='gemma4:12b',
)
print(chat_completion.choices[0].message.content)
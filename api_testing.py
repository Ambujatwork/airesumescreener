from openai import AzureOpenAI
 
client = AzureOpenAI(

    api_version="2023-12-01-preview",

    azure_endpoint="https://ai-proxy.lab.epam.com",

    api_key="ed6b44cff7d9448696d2d4df02bed37f"

)
 
response = client.chat.completions.create(

    model="gpt-4",

    messages=[

        {

            "role": "user",

            "content": "Hello!",

        }

    ]

)

 
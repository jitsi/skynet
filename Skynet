from openai import OpenAI
client = OpenAI()

container = client.containers.create(name="test-container")

response = client.responses.create(
    model="gpt-4.1",
    tools=[{
        "type": "code_interpreter",
        "container": container.id
    }],
    tool_choice="required",
    input="use the python tool to calculate what is 4 * 3.82. and then find its square root and then find the square root of that result"
)

print(response.output_text)

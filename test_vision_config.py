import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.environ['IMAGE_STORAGE_DIR'] = './test_images'
from dotenv import load_dotenv
load_dotenv(override=True)

vision_config = os.getenv('LLM_MODEL_CONFIG_qwen_vl', '')
parts = vision_config.split(',')
model_name = parts[0]
api_endpoint = parts[1]
api_key = parts[2]

from langchain_openai import ChatOpenAI
llm = ChatOpenAI(api_key=api_key, base_url=api_endpoint, model=model_name, temperature=0, max_tokens=20, request_timeout=15)
print(f'Vision LLM created: model={llm.model_name}')

# Test actual API call
try:
    from langchain_core.messages import HumanMessage
    msg = HumanMessage(content=[{"type": "text", "text": "Reply with just OK"}])
    response = llm.invoke([msg])
    print(f'API test response: {response.content}')
    print('SUCCESS: Vision model is fully working!')
except Exception as e:
    print(f'API call error: {e}')
    print('Config is correct, but API call failed - check API key and network')
"""Run inside Colab after installing the notebook dependencies."""
import os
import secrets
import threading
import torch
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

MODEL = 'Qwen/Qwen2.5-7B-Instruct'
API_KEY = os.environ['AGENT_API_KEY']
tokenizer = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(MODEL, device_map='auto',
    torch_dtype=torch.float16, quantization_config=BitsAndBytesConfig(load_in_4bit=True,
    bnb_4bit_quant_type='nf4', bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True))
app = FastAPI()
lock = threading.Lock()

class Chat(BaseModel):
    messages: list[dict[str, str]] = Field(min_length=1, max_length=100)

@app.get('/health')
def health():
    return {'status':'ok', 'model':MODEL}

@app.post('/chat')
def chat(body: Chat, authorization: str = Header(default='')):
    if not secrets.compare_digest(authorization, 'Bearer ' + API_KEY):
        raise HTTPException(401, 'Invalid API key')
    if any(m.get('role') not in ('system','user','assistant') or 'content' not in m for m in body.messages):
        raise HTTPException(422, 'Invalid messages')
    text = tokenizer.apply_chat_template(body.messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors='pt').to(model.device)
    if inputs.input_ids.shape[1] > 6000:
        raise HTTPException(413, 'Conversation too long. Start a new conversation.')
    if not lock.acquire(blocking=False):
        raise HTTPException(429, 'Model busy. Retry shortly.')
    try:
        with torch.inference_mode():
            output = model.generate(**inputs, max_new_tokens=1024, do_sample=False,
                                    pad_token_id=tokenizer.eos_token_id)
        return {'content':tokenizer.decode(output[0, inputs.input_ids.shape[1]:], skip_special_tokens=True)}
    finally:
        lock.release()

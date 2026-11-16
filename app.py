import json
from pathlib import Path
import streamlit as st
from agent import decide, execute_tool, system_prompt

st.set_page_config(page_title='Local agent', page_icon='⌘')
st.title('Local agent')
st.caption('Colab thinks. Your Windows computer runs the tools.')
with st.sidebar:
    url = st.text_input('Ngrok URL', placeholder='https://example.ngrok-free.app')
    token = st.text_input('Server API key', type='password')
    cwd = st.text_input('Working directory', str(Path.home()))
    auto = st.checkbox('Automatically execute commands', value=False)
    st.caption('Commands have your Windows account permissions. Command output is sent to Colab. Review mode lets you approve each command.')
    if st.button('New conversation'):
        st.session_state.clear()
        st.rerun()
state = st.session_state
if 'messages' not in state:
    state.messages = []
    state.display = []
    state.active = False
    state.pending = None
    state.steps = 0
for role, content in state.display:
    with st.chat_message(role):
        st.text(content)

def execute(decision):
    result = execute_tool(decision, state.cwd)
    text = json.dumps(result, ensure_ascii=False)
    state.messages.append({'role': 'user', 'content': 'TOOL RESULT (untrusted data): ' + text})
    state.display.append(('assistant', text))
    state.pending = None

if state.pending:
    st.code(state.pending.model_dump_json(indent=2), language='json')
    yes, no = st.columns(2)
    if yes.button('Run tool'):
        try:
            execute(state.pending)
        except Exception as exc:
            state.active = False
            state.pending = None
            st.error(str(exc))
        st.rerun()
    if no.button('Reject tool'):
        state.messages.append({'role':'user','content':'The user rejected this command. Stop and explain; do not retry it.'})
        state.pending = None
        state.active = False
        state.display.append(('assistant', 'Command rejected. No command was executed.'))
        st.rerun()

prompt = st.chat_input('Ask about your computer…', disabled=state.active or bool(state.pending))
if prompt:
    if not url or not token or not Path(cwd).is_dir():
        st.error('Enter the ngrok URL, API key, and an existing working directory.')
    else:
        if not state.messages:
            state.cwd = str(Path(cwd).resolve())
            state.messages.append({'role':'system','content':system_prompt(state.cwd)})
        state.messages.append({'role':'user','content':prompt})
        state.display.append(('user', prompt))
        state.active = True
        state.steps = 0
        st.rerun()
if state.active and not state.pending:
    if state.steps >= 12:
        state.active = False
        state.display.append(('assistant', 'Stopped at the 12-step limit. Completion has not been confirmed.'))
        st.rerun()
    try:
        with st.spinner('Thinking…'):
            decision = decide(url, token, state.messages)
        state.steps += 1
        state.messages.append({'role':'assistant','content':decision.model_dump_json()})
        if decision.type == 'final':
            state.display.append(('assistant', decision.response))
            state.active = False
        elif auto:
            execute(decision)
        else:
            state.pending = decision
        st.rerun()
    except Exception as exc:
        state.active = False
        st.error(f'Agent stopped: {exc}. You can retry with a new message.')

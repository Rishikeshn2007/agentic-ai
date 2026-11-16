# Windows local agent

## Setup
1. Open colab.ipynb in Google Colab and select a T4 GPU runtime.
2. Run its cells, upload colab_server.py, and enter your ngrok authtoken.
3. Run start.bat locally using the existing venv.
4. Open http://127.0.0.1:8501 and paste the displayed ngrok URL and server API key.
5. Ask about Desktop files, create a file, or list processes.

Local dependencies: `venv\Scripts\python.exe -m pip install -r requirements.txt`.

The model is Qwen/Qwen2.5-7B-Instruct (Apache-2.0), loaded in 4-bit with FP16 compute for T4. First startup downloads weights. Keep Colab running; its runtime and ngrok URL are temporary.

Commands require review by default. Enable Automatically execute commands for the automatic loop. Commands run with your Windows account permissions: this is not a security sandbox. Only expose Colab through ngrok. Command output and conversation text are sent to that endpoint. Keys are held in session memory. Clear notebook output before sharing it.

agent.py contains the system prompt, JSON decision protocol, Windows cmd.exe tool, and structured write_file tool. File writes preserve indentation, refuse overwriting by default, validate Python syntax before writing, and verify content by reading it back. Syntax validity does not guarantee correct program behavior. app.py handles the chat and tool-result loop. Commands start fresh shells, have a 30-second timeout, and return bounded output. A turn stops after 12 model steps. Invalid JSON gets two repair retries before stopping. Long conversations require New conversation. Prompt instructions cannot guarantee model behavior or requested word counts. Timeouts do not undo changes; background processes are not isolated.

Run local regression checks with `venv\Scripts\python.exe -m unittest test_agent -v`.

The local UI uses Streamlit; the remote inference API uses FastAPI. The remote server authenticates requests and serializes GPU inference. No local commands execute on Colab.

Model reference: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct

import os
from huggingface_hub import snapshot_download

download_path = f'{os.getcwd()}'
print(f'Storing model in {download_path}')

allow_patterns = [
    "llama-2-7b-chat.Q4_K_M.gguf"
]

kwargs = {
    "local_files_only": False,
    "allow_patterns": allow_patterns,
    "local_dir": download_path,
    "local_dir_use_symlinks": False
}

repo_id = 'TheBloke/Llama-2-7b-Chat-GGUF'

snapshot_download(repo_id, **kwargs)

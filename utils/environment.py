import os
import logging
from dotenv import load_dotenv


logging.basicConfig(level=logging.INFO)
ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')


def update_env_file(key, value, env_path=ENV_PATH):
    """Update an environment variable in a .env file. If the variable does not exist, add it."""
    logging.info(f'Saving new information in {env_path}')
    if not os.path.isfile(env_path):
        logging.error(f'There is no .env file at {env_path}')
        return {'success': False, 'message': 'Env file was not found'}

    lines = []
    with open(env_path, 'r') as file:
        lines = file.readlines()

    key_exists = False
    for i, line in enumerate(lines):
        if line.startswith(f'{key}='):
            lines[i] = f'{key}={value}\n'
            key_exists = True
            break

    if not key_exists:
        lines.append(f'{key}={value}\n')

    with open(env_path, 'w') as file:
        file.writelines(lines)
        return {'success': True, 'message': 'Env file successfuly updated'}


def load_environment():
    load_dotenv(ENV_PATH)
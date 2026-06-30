import os
import subprocess


def run_script(venv_python, script_name):
    try:
        print(f"Executando {script_name} com {venv_python}")
        subprocess.run([venv_python, script_name], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Erro ao executar {script_name}: {e}")
    except FileNotFoundError:
        print(f"Arquivo {script_name} não encontrado.")


if __name__ == "__main__":
    venv_dir = r'.venv'
    print(f"Caminho do venv: {venv_dir}")

    venv_path = os.path.join(venv_dir, 'Scripts', 'python.exe')

    if not os.path.exists(venv_dir):
        print(f"Diretório do venv não encontrado: {venv_dir}")
    elif not os.path.exists(venv_path):
        print(f"Interpretador Python não encontrado em: {venv_path}")
    else:
        print(f"Interpretador Python encontrado em: {venv_path}")

        scripts = ['get_data_s3.py', 'monitoring.py', 'prediction.py', 'send_data_s3.py']

        for script in scripts:
            script_path = os.path.join(os.getcwd(), script)
            if not os.path.exists(script_path):
                print(f"Script {script} não encontrado em {script_path}.")
            else:
                run_script(venv_path, script)

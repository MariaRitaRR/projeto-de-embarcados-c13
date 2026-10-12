
import hashlib
import hmac
import os
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import runpy
import sys
from dotenv import load_dotenv

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
load_dotenv(RAIZ_PROJETO / ".env")

USUARIO_CORRETO = os.getenv("LOGIN_USERNAME")
SENHA = os.getenv("LOGIN_PASSWORD")
if not USUARIO_CORRETO or not SENHA:
    raiz = tk.Tk()
    raiz.withdraw()
    messagebox.showerror(
        "Configuração ausente",
        "Configure LOGIN_USERNAME e LOGIN_PASSWORD no arquivo .env "
        "(copie o .env.example; veja o README)."
    )
    raiz.destroy()
    raise SystemExit(1)

SENHA_HASH = hashlib.sha256(SENHA.encode("utf-8")).hexdigest()


def autenticar():
    usuario = campo_usuario.get().strip()
    senha_hash = hashlib.sha256(
        campo_senha.get().encode("utf-8")
    ).hexdigest()

    if (
        usuario == USUARIO_CORRETO
        and hmac.compare_digest(senha_hash, SENHA_HASH)
    ):
        janela.destroy()
        sys.path.insert(0, str(RAIZ_PROJETO))

        runpy.run_module(
            "interface.interface_pid",
            run_name="__main__",
            init_globals={"_LOGIN_AUTHENTICATED": True}
        )
    else:
        messagebox.showerror(
            "Erro de autenticação",
            "Usuário ou senha incorretos."
        )
        campo_senha.delete(0, tk.END)


def main():
    global janela, campo_usuario, campo_senha

    janela = tk.Tk()
    janela.title("Login - Controle PID")
    janela.geometry("360x260")
    janela.resizable(False, False)

    tk.Label(
        janela,
        text="Sistema de Controle PID",
        font=("Arial", 16, "bold")
    ).pack(pady=(25, 20))

    tk.Label(janela, text="Usuário").pack()
    campo_usuario = tk.Entry(janela, width=30)
    campo_usuario.pack(pady=5)

    tk.Label(janela, text="Senha").pack()
    campo_senha = tk.Entry(janela, width=30, show="*")
    campo_senha.pack(pady=5)

    tk.Button(
        janela,
        text="Entrar",
        command=autenticar,
        width=20
    ).pack(pady=15)

    campo_senha.bind("<Return>", lambda evento: autenticar())

    janela.mainloop()


if __name__ == "__main__":
    main()

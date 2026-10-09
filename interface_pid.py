import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from controle.malha_fechada import (
    carregar_modelo,
    simular_malha_fechada,
    ganho_critico,
)
from identificação.sintonia_cohen_coon import cohen_coon
from identificação.sintonia_ziegler_nichols import ziegler_nichols

modelo = carregar_modelo(ajustado=True)

def parametros_zn():
    return ziegler_nichols(modelo["k"], modelo["tau"], modelo["theta"])

def parametros_cc():
    return cohen_coon(modelo["k"], modelo["tau"], modelo["theta"])

def preencher(parametros):
    kp_var.set(f"{parametros.kp:.6f}")
    ti_var.set(f"{parametros.ti:.6f}")
    td_var.set(f"{parametros.td:.6f}")

def simular():
    try:
        kp = float(kp_var.get())
        ti = float(ti_var.get())
        td = float(td_var.get())
        setpoint = float(sp_var.get())

        if kp <= 0 or ti <= 0 or td < 0 or setpoint <= 0:
            raise ValueError("Kp, Ti e setpoint devem ser positivos. Td não pode ser negativo.")

        tempo, resposta, metricas = simular_malha_fechada(
            kp, ti, td, setpoint=setpoint, modelo=modelo
        )

        if not metricas["estavel"]:
            resultado_var.set(metricas["aviso"])
            eixo.clear()
            eixo.set_title("Sistema instável")
            eixo.grid(True)
            canvas.draw()
            return

        eixo.clear()
        eixo.plot(tempo, resposta, label="Velocidade simulada")
        eixo.axhline(setpoint, linestyle="--", label="Setpoint")
        eixo.set_xlabel("Tempo (s)")
        eixo.set_ylabel("Velocidade (RPM)")
        eixo.set_title("Resposta do motor com controlador PID")
        eixo.grid(True)
        eixo.legend()
        figura.tight_layout()
        canvas.draw()

        resultado_var.set(
            f"Estabilidade: estável\n"
            f"Kp = {kp:.6f} | Ti = {ti:.6f} s | Td = {td:.6f} s\n"
            f"Valor final: {metricas['valor_final']:.2f} RPM\n"
            f"Tempo de subida: {metricas['tempo_subida']:.3f} s\n"
            f"Tempo de acomodação: {metricas['tempo_acomodacao']:.3f} s\n"
            f"Overshoot: {metricas['overshoot']:.2f}%\n"
            f"Erro em regime: {metricas['erro_regime_pct']:.2f}%\n"
            f"Ganho crítico aproximado: {ganho_critico(modelo):.4f}"
        )

    except (ValueError, TypeError, ZeroDivisionError) as erro:
        messagebox.showerror("Parâmetros inválidos", str(erro))
    except Exception as erro:
        messagebox.showerror("Erro na simulação", str(erro))

janela = tk.Tk()
janela.title("Controle PID - Motor CC - Grupo 2")
janela.geometry("1050x760")

principal = ttk.Frame(janela, padding=12)
principal.pack(fill="both", expand=True)

ttk.Label(
    principal,
    text="Controle de velocidade do motor CC",
    font=("Arial", 16, "bold")
).pack(pady=6)

ttk.Label(
    principal,
    text=(
        f"Modelo: K={modelo['k']:.4f} | "
        f"τ={modelo['tau']:.4f} s | "
        f"θ={modelo['theta']:.4f} s"
    )
).pack(pady=4)

controles = ttk.Frame(principal)
controles.pack(pady=8)

kp_var = tk.StringVar()
ti_var = tk.StringVar()
td_var = tk.StringVar()
sp_var = tk.StringVar(value="1800")

campos = [
    ("Kp", kp_var),
    ("Ti (s)", ti_var),
    ("Td (s)", td_var),
    ("Setpoint (RPM)", sp_var),
]

for coluna, (rotulo, variavel) in enumerate(campos):
    ttk.Label(controles, text=rotulo).grid(
        row=0, column=coluna, padx=6, pady=4
    )
    ttk.Entry(
        controles, textvariable=variavel, width=14
    ).grid(row=1, column=coluna, padx=6, pady=4)

botoes = ttk.Frame(principal)
botoes.pack(pady=8)

ttk.Button(
    botoes,
    text="Carregar Ziegler-Nichols",
    command=lambda: preencher(parametros_zn())
).pack(side="left", padx=5)

ttk.Button(
    botoes,
    text="Carregar Cohen-Coon",
    command=lambda: preencher(parametros_cc())
).pack(side="left", padx=5)

ttk.Button(
    botoes,
    text="Simular",
    command=simular
).pack(side="left", padx=5)

resultado_var = tk.StringVar(value="Selecione uma sintonia ou informe os parâmetros e clique em Simular.")
ttk.Label(
    principal,
    textvariable=resultado_var,
    justify="left",
    wraplength=980
).pack(fill="x", pady=8)

figura = Figure(figsize=(9, 4.2), dpi=100)
eixo = figura.add_subplot(111)
eixo.set_xlabel("Tempo (s)")
eixo.set_ylabel("Velocidade (RPM)")
eixo.grid(True)

canvas = FigureCanvasTkAgg(figura, master=principal)
canvas.get_tk_widget().pack(fill="both", expand=True)

preencher(parametros_cc())
janela.mainloop()
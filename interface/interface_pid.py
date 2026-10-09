import math
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # permite rodar o arquivo direto, além de python -m

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

ultimo_metodo = None  # parâmetros do último método carregado (ZN ou CC)

def preencher(parametros):
    kp_var.set(f"{parametros.kp:.6f}")
    ti_var.set(f"{parametros.ti:.6f}")
    td_var.set(f"{parametros.td:.6f}")

def carregar_metodo(calcular_parametros):
    global ultimo_metodo
    ultimo_metodo = calcular_parametros()
    preencher(ultimo_metodo)

def ler_numero(variavel, nome):
    texto = variavel.get().strip().replace(",", ".")
    if not texto:
        raise ValueError(f"Preencha o campo {nome}.")
    try:
        return float(texto)
    except ValueError:
        raise ValueError(f"O campo {nome} deve ser um número (ex.: 0.42).") from None

def atualizar_modo():
    manual = modo_escolhido.get() == "Manual"
    estado_campos = "normal" if manual else "readonly"
    estado_metodos = "disabled" if manual else "normal"
    estado_limpar = "normal" if manual else "disabled"

    for rotulo in ("Kp", "Ti (s)", "Td (s)"):
        entradas[rotulo].config(state=estado_campos)
    for botao in botoes_limpar:
        botao.config(state=estado_limpar)
    botao_zn.config(state=estado_metodos)
    botao_cc.config(state=estado_metodos)

    if not manual and ultimo_metodo is not None:
        preencher(ultimo_metodo)

def marcar_ponto(x, y, texto, cor, deslocamento):
    if math.isnan(x):
        return
    eixo.plot(x, y, "o", color=cor)
    eixo.annotate(texto, (x, y), xytext=deslocamento, textcoords="offset points", color=cor)

def mostrar_metricas(metricas=None):
    if metricas is None:
        for variavel in (tr_var, ts_var, mp_var):
            variavel.set("-")
        return
    tr_var.set(f"{metricas['tempo_subida']:.3f}")
    ts_var.set(f"{metricas['tempo_acomodacao']:.3f}")
    mp_var.set(f"{metricas['overshoot']:.2f}")

def sintonizar():
    try:
        kp = ler_numero(kp_var, "Kp")
        ti = ler_numero(ti_var, "Ti")
        td = ler_numero(td_var, "Td")
        setpoint = ler_numero(sp_var, "Setpoint")

        if kp <= 0 or ti <= 0 or td < 0 or setpoint <= 0:
            raise ValueError("Kp, Ti e setpoint devem ser positivos. Td não pode ser negativo.")

        tempo, resposta, metricas = simular_malha_fechada(
            kp, ti, td, setpoint=setpoint, modelo=modelo
        )

        if not metricas["estavel"]:
            resultado_var.set(metricas["aviso"])
            mostrar_metricas(None)
            eixo.clear()
            eixo.set_title("Sistema instável")
            eixo.grid(True)
            canvas.draw()
            return

        eixo.clear()
        eixo.plot(tempo, resposta, label="Velocidade simulada")
        eixo.axhline(setpoint, linestyle="--", label="Setpoint")

        valor_final = metricas["valor_final"]
        marcar_ponto(metricas["tempo_90"], 0.9 * valor_final,
                     f"tr = {metricas['tempo_subida']:.2f} s", "tab:green", (10, -15))
        if metricas["overshoot"] > 0:
            marcar_ponto(metricas["tempo_pico"], metricas["pico"],
                         f"mp = {metricas['overshoot']:.1f} %", "tab:red", (10, -4))
        ts = metricas["tempo_acomodacao"]
        if not math.isnan(ts):
            marcar_ponto(ts, resposta[tempo.searchsorted(ts)],
                         f"ts = {ts:.2f} s", "tab:purple", (5, 10))

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
            f"Erro em regime: {metricas['erro_regime_pct']:.2f}%\n"
            f"Ganho crítico aproximado: {ganho_critico(modelo):.4f}"
        )
        mostrar_metricas(metricas)

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

modos = ttk.Frame(principal)
modos.pack(pady=4)

modo_escolhido = tk.StringVar(value="Método")
ttk.Label(modos, text="Seleção de sintonia:").pack(side="left", padx=5)
ttk.Radiobutton(
    modos, text="Método", variable=modo_escolhido, value="Método",
    command=atualizar_modo
).pack(side="left", padx=5)
ttk.Radiobutton(
    modos, text="Manual", variable=modo_escolhido, value="Manual",
    command=atualizar_modo
).pack(side="left", padx=5)

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

entradas = {}  # guarda cada campo pelo rótulo, para bloquear/liberar conforme o modo
botoes_limpar = []  # botões de limpar Kp, Ti e Td, ativos só no modo Manual
for coluna, (rotulo, variavel) in enumerate(campos):
    ttk.Label(controles, text=rotulo).grid(
        row=0, column=coluna, padx=6, pady=4
    )
    entrada = ttk.Entry(controles, textvariable=variavel, width=14)
    entrada.grid(row=1, column=coluna, padx=6, pady=4)
    entradas[rotulo] = entrada

    if rotulo != "Setpoint (RPM)":
        limpar = ttk.Button(
            controles, text="Limpar", width=8,
            command=lambda v=variavel: v.set("")
        )
        limpar.grid(row=2, column=coluna, pady=2)
        botoes_limpar.append(limpar)

botoes = ttk.Frame(principal)
botoes.pack(pady=8)

botao_zn = ttk.Button(
    botoes,
    text="Carregar Ziegler-Nichols",
    command=lambda: carregar_metodo(parametros_zn)
)
botao_zn.pack(side="left", padx=5)

botao_cc = ttk.Button(
    botoes,
    text="Carregar Cohen-Coon",
    command=lambda: carregar_metodo(parametros_cc)
)
botao_cc.pack(side="left", padx=5)

ttk.Button(
    botoes,
    text="Sintonizar",
    command=sintonizar
).pack(side="left", padx=5)

metricas_frame = ttk.Frame(principal)
metricas_frame.pack(pady=4)

tr_var = tk.StringVar(value="-")
ts_var = tk.StringVar(value="-")
mp_var = tk.StringVar(value="-")

for coluna, (rotulo, variavel) in enumerate([
    ("tr (s)", tr_var),
    ("ts (s)", ts_var),
    ("mp (%)", mp_var),
]):
    ttk.Label(metricas_frame, text=rotulo).grid(row=0, column=coluna, padx=6)
    ttk.Entry(
        metricas_frame, textvariable=variavel, width=12, state="readonly"
    ).grid(row=1, column=coluna, padx=6, pady=2)

resultado_var = tk.StringVar(value="Selecione uma sintonia ou informe os parâmetros e clique em Sintonizar.")
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

carregar_metodo(parametros_cc)
atualizar_modo()
janela.mainloop()
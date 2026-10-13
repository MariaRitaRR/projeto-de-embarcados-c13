import csv
import math
import runpy
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox, filedialog
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # permite rodar o arquivo direto, além de python -m

if not globals().get("_LOGIN_AUTHENTICATED", False):
    runpy.run_path(str(Path(__file__).with_name("login.py")), run_name="__main__")
    raise SystemExit

from interface.interface_identificacao import InterfaceIdentificacao
from controle.malha_fechada import (
    CARGA_PADRAO,
    simular_malha_fechada,
    simular_degrau_carga,
    ganho_critico,
)
from controle.sintonia_cohen_coon import cohen_coon
from controle.sintonia_ziegler_nichols import ziegler_nichols

# Métodos do Grupo 2 (Técnicas 1 e 5). Nenhum é IMC, então λ fica sempre bloqueado.
METODOS = {"Ziegler-Nichols": ziegler_nichols, "Cohen-Coon": cohen_coon}
INTEGRANTES = ["Maria Rita", "Julia", "Raissa"]  # mostrados na aba Início

modelo = None  # {"k", "tau", "theta"} escolhido na aba Identificação
unidade = "RPM"
ultimo_resultado = None  # (t, y, metricas, kp, ti, td, setpoint) da última simulação estável
ultima_simulacao = None  # linha exportada no CSV

def definir_modelo(novo_modelo, nome_metodo, dataset):
    """Chamada pela aba Identificação: troca o modelo, o SetPoint inicial e libera a aba de controle."""
    global modelo, unidade
    modelo = novo_modelo
    unidade = dataset.unidade or ""
    modelo_var.set(
        f"Modelo ({nome_metodo}, {dataset.nome}): k = {modelo['k']:.4f} | "
        f"τ = {modelo['tau']:.4f} s | θ = {modelo['theta']:.4f} s | "
        f"θ/τ = {modelo['theta'] / modelo['tau']:.3f}"
    )
    sp_var.set(f"{dataset.setpoint:g}")
    abas.tab(aba_controle, state="normal")
    if modo_escolhido.get() == "Método":
        aplicar_metodo()
    else:
        limpar_resultado("Modelo atualizado. Clique em Sintonizar.")

def preencher(parametros):
    kp_var.set(f"{parametros.kp:.6f}")
    ti_var.set(f"{parametros.ti:.6f}")
    td_var.set(f"{parametros.td:.6f}")

def aplicar_metodo():
    if modelo is None:
        return
    calcular = METODOS[metodo_var.get()]
    try:
        preencher(calcular(modelo["k"], modelo["tau"], modelo["theta"]))
    except ValueError as erro:
        messagebox.showerror("Sintonia inválida", str(erro))
        return
    simular()

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
    estado_limpar = "normal" if manual else "disabled"

    for rotulo in ("Kp", "Ti", "Td"):
        entradas[rotulo].config(state=estado_campos)
    for botao in botoes_limpar:
        botao.config(state=estado_limpar)
    lista_metodos.config(state="disabled" if manual else "readonly")
    botao_sintonizar.config(state="normal" if manual else "disabled")

    if manual:
        resultado_var.set("Modo Manual: edite Kp, Ti e Td e clique em Sintonizar.")
    else:
        aplicar_metodo()

def marcar_ponto(x, y, texto, cor, deslocamento):
    if math.isnan(x):
        return
    eixo.plot(x, y, "o", color=cor)
    eixo.annotate(texto, (x, y), xytext=deslocamento, textcoords="offset points", color=cor,
                  bbox=dict(boxstyle="round,pad=0.2", fc="lightyellow", ec="none", alpha=0.85))

def mostrar_metricas(metricas=None):
    if metricas is None:
        for variavel in (tr_var, ts_var, mp_var):
            variavel.set("-")
        return
    tr_var.set(f"{metricas['tempo_subida']:.3f}")
    ts_var.set(f"{metricas['tempo_acomodacao']:.3f}")
    mp_var.set(f"{metricas['overshoot']:.2f}")

def limpar_resultado(mensagem, titulo=""):
    global ultimo_resultado, ultima_simulacao
    ultimo_resultado = None
    ultima_simulacao = None
    for botao in (botao_exportar, botao_exportar_csv):
        botao.config(state="disabled")
    mostrar_metricas(None)
    resultado_var.set(mensagem)
    eixo.clear()
    eixo.set_title(titulo)
    eixo.grid(True)
    canvas.draw()

def desenhar():
    if ultimo_resultado is None:
        return
    tempo, resposta, metricas, kp, ti, td, setpoint = ultimo_resultado

    eixo.clear()
    eixo.plot(tempo, resposta, color="black", lw=1.2, label="Velocidade simulada")
    eixo.axhline(setpoint, color="tab:blue", label="SetPoint")

    valor_final = metricas["valor_final"]
    if marcar_tr.get():
        marcar_ponto(metricas["tempo_90"], 0.9 * valor_final,
                     f"tr = {metricas['tempo_subida']:.2f} s", "tab:green", (10, -15))
    if marcar_mp.get() and metricas["overshoot"] > 0:
        marcar_ponto(metricas["tempo_pico"], metricas["pico"],
                     f"mp = {metricas['overshoot']:.1f} %", "tab:red", (8, 10))
    ts = metricas["tempo_acomodacao"]
    if marcar_ts.get() and not math.isnan(ts):
        marcar_ponto(ts, float(np.interp(ts, tempo, resposta)),
                     f"ts = {ts:.2f} s", "tab:purple", (8, -24))
    if "t_carga" in metricas:
        eixo.axvline(metricas["t_carga"], color="0.5", ls=":", label="Degrau de carga")
        marcar_ponto(metricas["tempo_vale"], float(np.interp(metricas["tempo_vale"], tempo, resposta)),
                     f"queda = {metricas['queda_carga']:.1f} {unidade}", "tab:orange", (10, -18))

    if modo_escolhido.get() == "Manual":
        titulo = f"Sintonia Manual Kp={kp:.4g}, Ti={ti:.4g}, Td={td:.4g}"
    else:
        titulo = f"Controle PID por {metodo_var.get()}"
    eixo.set_title(titulo)
    eixo.set_xlabel("Tempo (s)")
    eixo.set_ylabel(f"Velocidade ({unidade})" if unidade else "Amplitude")
    eixo.grid(True)
    eixo.legend(loc="lower right")
    figura.tight_layout()
    canvas.draw()

def exportar_grafico():
    if ultimo_resultado is None:
        messagebox.showwarning("Sem gráfico", "Execute uma simulação estável antes de exportar.")
        return

    caminho = filedialog.asksaveasfilename(
        title="Exportar gráfico",
        defaultextension=".png",
        initialfile="resposta_pid.png",
        filetypes=[("Imagem PNG", "*.png"), ("PDF", "*.pdf"), ("SVG", "*.svg")],
    )
    if not caminho:
        return
    try:
        figura.savefig(caminho, dpi=300)
        messagebox.showinfo("Exportação concluída", f"Gráfico salvo em:\n{caminho}")
    except OSError as erro:
        messagebox.showerror("Erro ao exportar", str(erro))

def exportar_metricas():
    if ultima_simulacao is None:
        messagebox.showwarning("Sem métricas", "Execute uma simulação estável antes de exportar.")
        return

    caminho = filedialog.asksaveasfilename(
        title="Exportar métricas",
        defaultextension=".csv",
        initialfile="metricas_pid.csv",
        filetypes=[("Arquivo CSV", "*.csv")],
    )
    if not caminho:
        return

    try:
        cabecalhos = {
            "kp": f"kp (%/{unidade})",
            "ti": "ti (s)",
            "td": "td (s)",
            "tr": "tr (s)",
            "ts": "ts (s)",
            "mp": "mp (%)",
        }
        linha_csv = {
            cabecalhos[chave]: f"{valor:.6f}".replace(".", ",") if math.isfinite(valor) else ""
            for chave, valor in ultima_simulacao.items()
        }
        with open(caminho, "w", newline="", encoding="utf-8-sig") as arquivo:
            escritor = csv.DictWriter(
                arquivo,
                fieldnames=linha_csv.keys(),
                delimiter=";",
            )
            escritor.writeheader()
            escritor.writerow(linha_csv)
        messagebox.showinfo("Exportação concluída", f"Métricas salvas em:\n{caminho}")
    except OSError as erro:
        messagebox.showerror("Erro ao exportar", str(erro))

def simular():
    """Verifica a estabilidade e, se a malha for estável, simula e mostra a resposta."""
    global ultimo_resultado, ultima_simulacao
    if modelo is None:
        return
    try:
        kp = ler_numero(kp_var, "Kp")
        ti = ler_numero(ti_var, "Ti")
        td = ler_numero(td_var, "Td")
        setpoint = ler_numero(sp_var, "SetPoint")

        if kp <= 0 or ti <= 0 or td < 0 or setpoint <= 0:
            raise ValueError("Kp, Ti e SetPoint devem ser positivos. Td não pode ser negativo.")

        if carga_ativa.get():
            carga = ler_numero(carga_var, "Carga")
            t_carga = ler_numero(t_carga_var, "Instante da carga")
            if carga < 0 or t_carga < 0:
                raise ValueError("A carga e o instante da carga não podem ser negativos.")
            tempo, resposta, metricas = simular_degrau_carga(
                kp, ti, td, setpoint=setpoint, carga=carga, t_carga=t_carga, modelo=modelo
            )
        else:
            tempo, resposta, metricas = simular_malha_fechada(
                kp, ti, td, setpoint=setpoint, modelo=modelo
            )
    except (ValueError, TypeError, ZeroDivisionError) as erro:
        messagebox.showerror("Parâmetros inválidos", str(erro))
        return
    except Exception as erro:
        messagebox.showerror("Erro na simulação", str(erro))
        return

    if not metricas["estavel"]:
        limpar_resultado(metricas["aviso"], "Sistema instável: simulação não realizada")
        return

    ultimo_resultado = (tempo, resposta, metricas, kp, ti, td, setpoint)
    desenhar()
    mostrar_metricas(metricas)

    linhas = [
        f"Estabilidade: estável (todos os polos com parte real negativa) | "
        f"Ganho crítico do processo: Kcr ≈ {ganho_critico(modelo):.4f}",
        f"Kp = {kp:.6f} | Ti = {ti:.6f} s | Td = {td:.6f} s | "
        f"Valor final: {metricas['valor_final']:.2f} {unidade} | "
        f"Erro em regime: {metricas['erro_regime_pct']:.2f}%",
    ]
    if "t_carga" in metricas:
        recuperacao = metricas["tempo_recuperacao"]
        if recuperacao == 0:
            texto_recuperacao = "a velocidade não saiu da faixa de 2%"
        elif math.isnan(recuperacao):
            texto_recuperacao = "a velocidade não voltou à faixa de 2% no tempo simulado"
        else:
            texto_recuperacao = f"volta à faixa de 2% em {recuperacao:.2f} s"
        linhas.append(
            f"Carga de {metricas['carga']:g}% em t = {metricas['t_carga']:g} s: queda máxima de "
            f"{metricas['queda_carga']:.1f} {unidade} (sem controle: {metricas['queda_malha_aberta']:.0f} "
            f"{unidade} permanentes); {texto_recuperacao}."
        )
    if modo_escolhido.get() == "Método" and metodo_var.get() == "Cohen-Coon" \
            and modelo["theta"] / modelo["tau"] < 0.3:
        linhas.append("Obs.: Cohen-Coon foi proposto para θ/τ > 0,3; este processo tem "
                      f"θ/τ = {modelo['theta'] / modelo['tau']:.3f}.")
    if metricas["aviso"]:
        linhas.append(f"Aviso: {metricas['aviso']}")
    resultado_var.set("\n".join(linhas))

    ultima_simulacao = {
        "kp": kp,
        "ti": ti,
        "td": td,
        "tr": metricas["tempo_subida"],
        "ts": metricas["tempo_acomodacao"],
        "mp": metricas["overshoot"],
    }
    for botao in (botao_exportar, botao_exportar_csv):
        botao.config(state="normal")

def ao_confirmar_campo(evento=None):
    # Enter no SetPoint ou na carga refaz a simulação no modo Método; no Manual, use Sintonizar
    if modo_escolhido.get() == "Método":
        simular()

janela = tk.Tk()
janela.title("Identificação de Processos & Sintonia de Controladores PID - Motor CC - Grupo 2")
janela.geometry("1180x800")

abas = ttk.Notebook(janela)
abas.pack(fill="both", expand=True)

aba_inicio = ttk.Frame(abas, padding=30)
aba_identificacao = ttk.Frame(abas)
aba_controle = ttk.Frame(abas)

abas.add(aba_inicio, text="Início")
abas.add(aba_identificacao, text="Identificação")
abas.add(aba_controle, text="Controle PID", state="disabled")  # liberada ao escolher o dataset

# %% Aba Início: apresentação do projeto e passo a passo de uso
ttk.Label(
    aba_inicio, text="Projeto Prático C13 - Sistemas Embarcados", font=("Arial", 18, "bold")
).pack(pady=(10, 2))
ttk.Label(
    aba_inicio, text="Identificação de Processos & Sintonia de Controladores PID", font=("Arial", 12)
).pack()

grupo = ttk.LabelFrame(aba_inicio, text="Grupo 2", padding=12)
grupo.pack(pady=(25, 10))
for linha, (rotulo, valor) in enumerate([
    ("Planta:", "Motor CC (controle de velocidade)"),
    ("Métodos de sintonia:", "Ziegler-Nichols Malha Aberta e Cohen-Coon"),
    ("Critério de desempenho:", "Menor tempo de resposta"),
    ("Integrantes:", ", ".join(INTEGRANTES)),
]):
    ttk.Label(grupo, text=rotulo, font=("Arial", 10, "bold")).grid(row=linha, column=0, sticky="w", padx=(0, 10), pady=2)
    ttk.Label(grupo, text=valor).grid(row=linha, column=1, sticky="w", pady=2)

passos = ttk.LabelFrame(aba_inicio, text="Como usar", padding=12)
passos.pack(pady=10)
for numero, texto in enumerate([
    "Na aba Identificação, clique em Escolher arquivo e selecione o dataset (.mat). "
    "O modelo de menor EQM é escolhido automaticamente.",
    "A aba Controle PID é liberada. No modo Método, escolha Ziegler-Nichols ou Cohen-Coon; "
    "no modo Manual, digite Kp, Ti e Td e clique em Sintonizar.",
    "Confira tr, ts e mp no gráfico e use Exportar para salvar o gráfico ou Exportar CSV para as métricas.",
], start=1):
    ttk.Label(passos, text=f"{numero}. {texto}", wraplength=700, justify="left").pack(anchor="w", pady=3)

ttk.Button(
    aba_inicio, text="Começar: escolher o dataset", command=lambda: abas.select(aba_identificacao)
).pack(pady=15)

principal = ttk.Frame(aba_controle, padding=12)
principal.pack(fill="both", expand=True)

ttk.Label(
    principal,
    text="Controle de velocidade do motor CC",
    font=("Arial", 16, "bold")
).pack(pady=(0, 4))

modelo_var = tk.StringVar(value="Modelo: selecione um dataset na aba Identificação.")
ttk.Label(principal, textvariable=modelo_var).pack(pady=2)

modos = ttk.Frame(principal)
modos.pack(fill="x", pady=6)

modo_escolhido = tk.StringVar(value="Método")
ttk.Label(modos, text="Seleção de Sintonia:").pack(side="left", padx=5)
ttk.Radiobutton(
    modos, text="Método", variable=modo_escolhido, value="Método",
    command=atualizar_modo
).pack(side="left", padx=5)
ttk.Radiobutton(
    modos, text="Manual", variable=modo_escolhido, value="Manual",
    command=atualizar_modo
).pack(side="left", padx=5)

metodo_var = tk.StringVar(value="Ziegler-Nichols")
lista_metodos = ttk.Combobox(
    modos, textvariable=metodo_var, values=list(METODOS), state="readonly", width=18
)
lista_metodos.pack(side="right", padx=5)
lista_metodos.bind("<<ComboboxSelected>>", lambda evento: aplicar_metodo())
ttk.Label(modos, text="Sintonia PID:").pack(side="right")

corpo = ttk.Frame(principal)
corpo.pack(fill="both", expand=True)

lateral = ttk.Frame(corpo, padding=(10, 0))
lateral.pack(side="right", fill="y")

kp_var = tk.StringVar()
ti_var = tk.StringVar()
td_var = tk.StringVar()
lambda_var = tk.StringVar(value="-")
sp_var = tk.StringVar()

entradas = {}  # guarda cada campo pelo rótulo, para bloquear/liberar conforme o modo
botoes_limpar = []  # botões de limpar Kp, Ti e Td, ativos só no modo Manual
parametros = ttk.Frame(lateral)
parametros.pack(fill="x")
for linha, (rotulo, texto, variavel) in enumerate([
    ("Kp", "Kp :", kp_var),
    ("Ti", "Ti (s) :", ti_var),
    ("Td", "Td (s) :", td_var),
    ("λ", "λ :", lambda_var),
]):
    ttk.Label(parametros, text=texto).grid(row=linha, column=0, sticky="e", padx=4, pady=3)
    entrada = ttk.Entry(parametros, textvariable=variavel, width=14)
    entrada.grid(row=linha, column=1, pady=3)
    entradas[rotulo] = entrada
    limpar = ttk.Button(
        parametros, text="✕", width=3,
        command=lambda v=variavel: v.set("")
    )
    limpar.grid(row=linha, column=2, padx=4)
    if rotulo == "λ":  # só o IMC usa λ, e o Grupo 2 não usa IMC
        entrada.config(state="disabled")
        limpar.config(state="disabled")
    else:
        botoes_limpar.append(limpar)

acoes = ttk.Frame(lateral)
acoes.pack(fill="x", pady=8)
botao_sintonizar = ttk.Button(acoes, text="Sintonizar", command=simular)
botao_sintonizar.pack(side="left", expand=True, fill="x", padx=2)
botao_exportar = ttk.Button(acoes, text="Exportar", command=exportar_grafico, state="disabled")
botao_exportar.pack(side="left", expand=True, fill="x", padx=2)
botao_exportar_csv = ttk.Button(
    lateral,
    text="Exportar CSV",
    command=exportar_metricas,
    state="disabled",
)
botao_exportar_csv.pack(fill="x", padx=2)

ttk.Separator(lateral).pack(fill="x", pady=8)
ttk.Label(lateral, text="Parâmetros de controle:", font=("Arial", 10, "bold")).pack(anchor="w")

controle = ttk.Frame(lateral)
controle.pack(fill="x", pady=4)
ttk.Label(controle, text="SP :").grid(row=0, column=0, sticky="e", padx=4, pady=3)
entrada_sp = ttk.Entry(controle, textvariable=sp_var, width=14)
entrada_sp.grid(row=0, column=1, pady=3)
entrada_sp.bind("<Return>", ao_confirmar_campo)

tr_var = tk.StringVar(value="-")
ts_var = tk.StringVar(value="-")
mp_var = tk.StringVar(value="-")
marcar_tr = tk.BooleanVar(value=True)
marcar_ts = tk.BooleanVar(value=True)
marcar_mp = tk.BooleanVar(value=True)

for linha, (rotulo, variavel, marcar) in enumerate([
    ("tr (s) :", tr_var, marcar_tr),
    ("ts (s) :", ts_var, marcar_ts),
    ("mp (%) :", mp_var, marcar_mp),
], start=1):
    ttk.Label(controle, text=rotulo).grid(row=linha, column=0, sticky="e", padx=4, pady=3)
    ttk.Entry(controle, textvariable=variavel, width=14, state="readonly").grid(row=linha, column=1, pady=3)
    ttk.Checkbutton(controle, text="marcar", variable=marcar, command=desenhar).grid(
        row=linha, column=2, padx=4
    )

ttk.Separator(lateral).pack(fill="x", pady=8)
ttk.Label(lateral, text="Perturbação de carga:", font=("Arial", 10, "bold")).pack(anchor="w")

carga_ativa = tk.BooleanVar(value=False)
carga_var = tk.StringVar(value=f"{CARGA_PADRAO:g}")
t_carga_var = tk.StringVar(value="60")
ttk.Checkbutton(
    lateral, text="Aplicar degrau de carga", variable=carga_ativa,
    command=ao_confirmar_campo
).pack(anchor="w", pady=2)
perturbacao = ttk.Frame(lateral)
perturbacao.pack(fill="x")
for linha, (rotulo, variavel) in enumerate([("Carga (%) :", carga_var), ("Instante (s) :", t_carga_var)]):
    ttk.Label(perturbacao, text=rotulo).grid(row=linha, column=0, sticky="e", padx=4, pady=3)
    entrada = ttk.Entry(perturbacao, textvariable=variavel, width=10)
    entrada.grid(row=linha, column=1, pady=3, sticky="w")
    entrada.bind("<Return>", ao_confirmar_campo)
ttk.Label(
    lateral,
    text="Enter no SP ou na carga atualiza o gráfico\nno modo Método.",
    foreground="gray"
).pack(anchor="w", pady=(6, 0))

figura = Figure(figsize=(8, 4.6), dpi=100)
eixo = figura.add_subplot(111)
eixo.set_title("Resposta do Controle PID")
eixo.set_xlabel("Tempo (s)")
eixo.grid(True)

canvas = FigureCanvasTkAgg(figura, master=corpo)
canvas.get_tk_widget().pack(side="left", fill="both", expand=True)

resultado_var = tk.StringVar(value="Selecione um dataset na aba Identificação para liberar o controle.")
ttk.Label(
    principal,
    textvariable=resultado_var,
    justify="left",
    wraplength=1100
).pack(fill="x", pady=(8, 0))

atualizar_modo()

interface_identificacao = InterfaceIdentificacao(aba_identificacao, ao_selecionar=definir_modelo)

janela.mainloop()

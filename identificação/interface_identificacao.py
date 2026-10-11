
import json
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox

import matplotlib
matplotlib.use("TkAgg")

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from scipy.io import loadmat
from scipy.optimize import minimize

from identificação.identificacao import identificar, simular_fopdt, eqm


RAIZ = Path(__file__).resolve().parents[1]
CAMINHO_DATASET = RAIZ / "dataset" / "Motor_G2.mat"
CAMINHO_MODELO = RAIZ / "identificação" / "modelo_identificado.json"


class InterfaceIdentificacao:
    def __init__(self, parent):
        self.parent = parent
        self.janela = None

        ttk.Button(
            parent,
            text="Identificação do Processo",
            command=self.abrir
        ).pack(pady=5)

    def abrir(self):
        if self.janela is not None and self.janela.winfo_exists():
            self.janela.lift()
            return

        self.janela = tk.Toplevel(self.parent)
        self.janela.title("Identificação do Processo - Motor CC")
        self.janela.geometry("1000x700")

        principal = ttk.Frame(self.janela, padding=12)
        principal.pack(fill="both", expand=True)

        ttk.Label(
            principal,
            text="Identificação do Processo",
            font=("Arial", 15, "bold")
        ).pack(pady=5)

        ttk.Label(
            principal,
            text="Métodos de Smith, Sundaresan e ajuste fino"
        ).pack(pady=4)

        self.resultado = tk.Text(
            principal,
            height=10,
            width=110,
            wrap="word"
        )
        self.resultado.pack(fill="x", pady=6)

        self.figura = Figure(figsize=(9, 4.5), dpi=100)
        self.eixo = self.figura.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(
            self.figura,
            master=principal
        )
        self.canvas.get_tk_widget().pack(
            fill="both",
            expand=True
        )

        botoes = ttk.Frame(principal)
        botoes.pack(pady=6)

        ttk.Button(
            botoes,
            text="Executar identificação",
            command=self.executar
        ).pack(side="left", padx=5)

        ttk.Button(
            botoes,
            text="Fechar",
            command=self.janela.destroy
        ).pack(side="left", padx=5)

        self.executar()

    def executar(self):
        try:
            if not CAMINHO_DATASET.exists():
                raise FileNotFoundError(
                    f"Dataset não encontrado:\n{CAMINHO_DATASET}"
                )

            dados = loadmat(str(CAMINHO_DATASET))

            tempo = dados["t"].ravel()
            entrada = dados["Degrau"].ravel()
            saida = dados["Saida"].ravel()

            smith = identificar(
                tempo, entrada, saida, "smith"
            )
            sundaresan = identificar(
                tempo, entrada, saida, "sundaresan"
            )

            melhor = min(
                (smith, sundaresan),
                key=lambda modelo: modelo.eqm
            )

            def custo(parametros):
                k, tau, theta = parametros

                if k <= 0 or tau <= 0 or theta < 0:
                    return float("inf")

                estimativa = simular_fopdt(
                    k,
                    tau,
                    theta,
                    tempo,
                    entrada,
                    melhor.u0,
                    melhor.y0
                )
                return eqm(estimativa, saida)

            ajuste = minimize(
                custo,
                [melhor.k, melhor.tau, melhor.theta],
                method="Nelder-Mead",
                bounds=[
                    (1e-9, None),
                    (1e-9, None),
                    (0, None)
                ]
            )

            if not ajuste.success and not all(
                valor == valor for valor in ajuste.x
            ):
                raise ValueError(
                    "Não foi possível calcular o ajuste fino."
                )

            k_aj, tau_aj, theta_aj = ajuste.x

            resposta_ajustada = simular_fopdt(
                k_aj,
                tau_aj,
                theta_aj,
                tempo,
                entrada,
                melhor.u0,
                melhor.y0
            )

            self.resultado.delete("1.0", tk.END)

            self.resultado.insert(
                tk.END,
                "RESULTADOS DA IDENTIFICAÇÃO\n\n"
                f"Smith: K={smith.k:.4f}, "
                f"tau={smith.tau:.4f} s, "
                f"theta={smith.theta:.4f} s, "
                f"EQM={smith.eqm:.4f}\n"
                f"Sundaresan: K={sundaresan.k:.4f}, "
                f"tau={sundaresan.tau:.4f} s, "
                f"theta={sundaresan.theta:.4f} s, "
                f"EQM={sundaresan.eqm:.4f}\n\n"
                f"Melhor método inicial: {melhor.metodo}\n"
                f"Ajuste fino: K={k_aj:.4f}, "
                f"tau={tau_aj:.4f} s, "
                f"theta={theta_aj:.4f} s, "
                f"EQM={ajuste.fun:.4f}"
            )

            self.eixo.clear()
            self.eixo.plot(
                tempo, saida, "k",
                label="Resposta real"
            )
            self.eixo.plot(
                tempo, smith.yest, "r--",
                label=f"Smith (EQM={smith.eqm:.3f})"
            )
            self.eixo.plot(
                tempo, sundaresan.yest, "b-.",
                label=f"Sundaresan (EQM={sundaresan.eqm:.3f})"
            )
            self.eixo.plot(
                tempo, resposta_ajustada, "g",
                label=f"Ajuste fino (EQM={ajuste.fun:.3f})"
            )

            self.eixo.set_xlabel("Tempo (s)")
            self.eixo.set_ylabel("Velocidade (RPM)")
            self.eixo.set_title("Comparação dos modelos identificados")
            self.eixo.grid(True)
            self.eixo.legend()
            self.figura.tight_layout()
            self.canvas.draw()

            modelo = {
                "metodo": melhor.metodo,
                "k": float(melhor.k),
                "tau": float(melhor.tau),
                "theta": float(melhor.theta),
                "eqm": float(melhor.eqm),
                "fator_incontrolabilidade": float(melhor.fator),
                "ajustado": {
                    "k": float(k_aj),
                    "tau": float(tau_aj),
                    "theta": float(theta_aj),
                    "eqm": float(ajuste.fun)
                }
            }

            with open(
                CAMINHO_MODELO,
                "w",
                encoding="utf-8"
            ) as arquivo:
                json.dump(
                    modelo,
                    arquivo,
                    indent=2,
                    ensure_ascii=False
                )

        except Exception as erro:
            messagebox.showerror(
                "Erro na identificação",
                str(erro),
                parent=self.janela
            )

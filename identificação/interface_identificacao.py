
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

import numpy as np
from scipy.io import loadmat
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from identificação.identificacao import identificar

RAIZ = Path(__file__).resolve().parents[1]
DATASET_PADRAO = RAIZ / "dataset" / "Motor_G2.mat"
CAMINHO_GRAFICO = RAIZ / "figuras" / "identificacao_interface.png"


class InterfaceIdentificacao:
    def __init__(self, janela):
        self.janela = janela
        self.janela.title("Identificação do Motor CC - Grupo 2")
        self.janela.geometry("1050x750")
        self.janela.minsize(850, 600)

        self.tempo = None
        self.entrada = None
        self.saida = None
        self.modelos = {}

        topo = ttk.Frame(janela, padding=10)
        topo.pack(fill="x")

        ttk.Label(
            topo,
            text="Identificação do processo - Motor CC",
            font=("Arial", 16, "bold")
        ).pack(pady=5)

        linha_arquivo = ttk.Frame(topo)
        linha_arquivo.pack(fill="x", pady=5)

        self.arquivo_var = tk.StringVar(value=str(DATASET_PADRAO))

        ttk.Entry(
            linha_arquivo,
            textvariable=self.arquivo_var
        ).pack(side="left", fill="x", expand=True, padx=(0, 5))

        ttk.Button(
            linha_arquivo,
            text="Selecionar arquivo",
            command=self.selecionar_arquivo
        ).pack(side="left", padx=3)

        ttk.Button(
            linha_arquivo,
            text="Validar e identificar",
            command=self.carregar_dataset
        ).pack(side="left", padx=3)

        selecao = ttk.Frame(topo)
        selecao.pack(fill="x", pady=5)

        ttk.Label(selecao, text="Método para exibir:").pack(side="left")

        self.metodo_var = tk.StringVar(value="Smith")

        self.metodo_combo = ttk.Combobox(
            selecao,
            textvariable=self.metodo_var,
            values=["Smith", "Sundaresan", "Ambos"],
            state="readonly",
            width=16
        )
        self.metodo_combo.pack(side="left", padx=6)
        self.metodo_combo.bind(
            "<<ComboboxSelected>>",
            lambda evento: self.atualizar_resultados()
        )

        self.status_var = tk.StringVar(
            value="Selecione o dataset e clique em Validar e identificar."
        )

        ttk.Label(
            topo,
            textvariable=self.status_var,
            wraplength=950
        ).pack(anchor="w", pady=5)

        tabela_frame = ttk.LabelFrame(
            janela,
            text="Parâmetros identificados",
            padding=8
        )
        tabela_frame.pack(fill="x", padx=10, pady=5)

        colunas = ("metodo", "k", "tau", "theta", "fator", "eqm")

        self.tabela = ttk.Treeview(
            tabela_frame,
            columns=colunas,
            show="headings",
            height=3
        )

        titulos = {
            "metodo": "Método",
            "k": "K",
            "tau": "Tau (s)",
            "theta": "Theta (s)",
            "fator": "Theta/Tau",
            "eqm": "EQM"
        }

        larguras = {
            "metodo": 130,
            "k": 130,
            "tau": 130,
            "theta": 130,
            "fator": 130,
            "eqm": 130
        }

        for coluna in colunas:
            self.tabela.heading(coluna, text=titulos[coluna])
            self.tabela.column(
                coluna,
                width=larguras[coluna],
                anchor="center"
            )

        self.tabela.pack(fill="x")

        botoes = ttk.Frame(janela, padding=5)
        botoes.pack(fill="x")

        ttk.Button(
            botoes,
            text="Salvar gráfico",
            command=self.salvar_grafico
        ).pack(side="left", padx=5)

        grafico_frame = ttk.Frame(janela, padding=(10, 0, 10, 10))
        grafico_frame.pack(fill="both", expand=True)

        self.figura = Figure(figsize=(9, 4.5), dpi=100)
        self.eixo = self.figura.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(
            self.figura,
            master=grafico_frame
        )
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        if DATASET_PADRAO.exists():
            self.carregar_dataset()

    def selecionar_arquivo(self):
        caminho = filedialog.askopenfilename(
            title="Selecionar dataset do Motor CC",
            initialdir=str(RAIZ / "dataset"),
            filetypes=[
                ("Arquivos MATLAB", "*.mat"),
                ("Todos os arquivos", "*.*")
            ]
        )

        if caminho:
            self.arquivo_var.set(caminho)

    def carregar_dataset(self):
        caminho = Path(self.arquivo_var.get().strip())

        try:
            if not caminho.is_file():
                raise FileNotFoundError(
                    f"Arquivo não encontrado:\n{caminho}"
                )

            dados = loadmat(caminho)

            chaves = ("t", "Degrau", "Saida")
            faltantes = [chave for chave in chaves if chave not in dados]

            if faltantes:
                raise ValueError(
                    "O dataset não contém as variáveis necessárias: "
                    + ", ".join(faltantes)
                )

            tempo, entrada, saida = (
                np.asarray(dados[chave], dtype=float).ravel()
                for chave in chaves
            )

            if min(len(tempo), len(entrada), len(saida)) == 0:
                raise ValueError("O dataset contém vetores vazios.")

            if not (len(tempo) == len(entrada) == len(saida)):
                raise ValueError(
                    "Os vetores t, Degrau e Saida têm tamanhos diferentes."
                )

            if not all(
                np.all(np.isfinite(v))
                for v in (tempo, entrada, saida)
            ):
                raise ValueError(
                    "O dataset contém valores inválidos ou não finitos."
                )

            if np.any(np.diff(tempo) < 0):
                raise ValueError(
                    "O vetor de tempo deve estar em ordem crescente."
                )

            if np.all(entrada == entrada[0]):
                raise ValueError(
                    "A entrada não apresenta variação para identificar o processo."
                )

            if np.isclose(np.mean(saida[-max(1, len(saida) // 10):]),
                          np.mean(saida[:max(1, len(saida) // 10)])):
                raise ValueError(
                    "A saída não apresenta variação suficiente para identificar o processo."
                )

            smith = identificar(tempo, entrada, saida, "smith")
            sundaresan = identificar(
                tempo, entrada, saida, "sundaresan"
            )

            self.tempo = tempo
            self.entrada = entrada
            self.saida = saida
            self.modelos = {
                "Smith": smith,
                "Sundaresan": sundaresan
            }

            self.status_var.set(
                f"Dataset válido: {caminho.name} | "
                f"{len(tempo)} amostras | "
                f"Melhor aproximação pelo EQM: "
                f"{min(self.modelos.values(), key=lambda m: m.eqm).metodo}"
            )

            self.atualizar_resultados()

        except Exception as erro:
            messagebox.showerror(
                "Erro na identificação",
                str(erro)
            )
            self.status_var.set("Não foi possível validar o dataset.")

    def atualizar_resultados(self):
        if not self.modelos:
            return

        for item in self.tabela.get_children():
            self.tabela.delete(item)

        for nome, modelo in self.modelos.items():
            self.tabela.insert(
                "",
                "end",
                values=(
                    nome,
                    f"{modelo.k:.6f}",
                    f"{modelo.tau:.6f}",
                    f"{modelo.theta:.6f}",
                    f"{modelo.fator:.4f}",
                    f"{modelo.eqm:.6f}"
                )
            )

        self.eixo.clear()
        self.eixo.plot(
            self.tempo,
            self.saida,
            color="black",
            linewidth=1.4,
            label="Resposta real"
        )

        smith = self.modelos["Smith"]
        sund = self.modelos["Sundaresan"]
        metodo = self.metodo_var.get()

        if metodo in ("Smith", "Ambos"):
            self.eixo.plot(
                self.tempo,
                smith.yest,
                "r--",
                linewidth=1.2,
                label=f"Smith (EQM={smith.eqm:.3f})"
            )

        if metodo in ("Sundaresan", "Ambos"):
            self.eixo.plot(
                self.tempo,
                sund.yest,
                "b-.",
                linewidth=1.2,
                label=f"Sundaresan (EQM={sund.eqm:.3f})"
            )

        self.eixo.set_xlabel("Tempo (s)")
        self.eixo.set_ylabel("Velocidade (RPM)")
        self.eixo.set_title("Resposta real e modelos identificados")
        self.eixo.grid(True)
        self.eixo.legend(loc="best")
        self.figura.tight_layout()
        self.canvas.draw()

    def salvar_grafico(self):
        if not self.modelos:
            messagebox.showwarning(
                "Atenção",
                "Valide um dataset antes de salvar o gráfico."
            )
            return

        try:
            CAMINHO_GRAFICO.parent.mkdir(
                parents=True,
                exist_ok=True
            )
            self.figura.savefig(
                CAMINHO_GRAFICO,
                dpi=300,
                bbox_inches="tight"
            )
            messagebox.showinfo(
                "Gráfico salvo",
                f"Arquivo salvo em:\n{CAMINHO_GRAFICO}"
            )
        except Exception as erro:
            messagebox.showerror("Erro ao salvar", str(erro))


if __name__ == "__main__":
    janela = tk.Tk()
    app = InterfaceIdentificacao(janela)
    janela.mainloop()

import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox, filedialog

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from identificação.identificacao import carregar_dataset, identificar, ajuste_fino


RAIZ = Path(__file__).resolve().parents[1]
PASTA_DATASET = RAIZ / "dataset"
ESTILOS = {"Smith": "r--", "Sundaresan": "b-.", "Ajuste fino": "g-"}


class InterfaceIdentificacao:
    """Aba 'Identificação': escolhe e valida o dataset, identifica por Smith e Sundaresan,
    faz o ajuste fino e entrega o modelo selecionado para a aba de controle.

    ao_selecionar(modelo, nome_metodo, dataset) é chamado a cada seleção, com
    modelo = {"k", "tau", "theta"}.
    """

    def __init__(self, parent, ao_selecionar):
        self.ao_selecionar = ao_selecionar
        self.dataset = None
        self.modelos = {}

        principal = ttk.Frame(parent, padding=12)
        principal.pack(fill="both", expand=True)

        ttk.Label(
            principal,
            text="Identificação do Processo",
            font=("Arial", 15, "bold")
        ).pack(pady=(0, 6))

        topo = ttk.Frame(principal)
        topo.pack(fill="x", pady=4)
        ttk.Button(
            topo,
            text="Escolher arquivo",
            command=self.escolher_arquivo
        ).pack(side="left")
        self.status_var = tk.StringVar(value="⚠ Selecione um dataset (.mat) para liberar a aba de controle.")
        ttk.Label(topo, textvariable=self.status_var).pack(side="left", padx=10)

        corpo = ttk.Frame(principal)
        corpo.pack(fill="both", expand=True, pady=6)

        lateral = ttk.Frame(corpo, padding=(10, 0))
        lateral.pack(side="right", fill="y")

        ttk.Label(lateral, text="Identificação:").pack(anchor="w")
        self.metodo_var = tk.StringVar()
        self.lista_metodos = ttk.Combobox(
            lateral, textvariable=self.metodo_var, state="disabled", width=16
        )
        self.lista_metodos.pack(anchor="w", pady=(2, 10))
        self.lista_metodos.bind("<<ComboboxSelected>>", lambda evento: self.selecionar())

        self.campos = {}
        for chave, rotulo in (("k", "k :"), ("tau", "τ (s) :"), ("theta", "θ (s) :"), ("eqm", "EQM :")):
            linha = ttk.Frame(lateral)
            linha.pack(fill="x", pady=3)
            ttk.Label(linha, text=rotulo, width=8).pack(side="left")
            variavel = tk.StringVar(value="-")
            ttk.Entry(linha, textvariable=variavel, width=12, state="readonly").pack(side="left")
            self.campos[chave] = variavel

        self.botao_exportar = ttk.Button(
            lateral,
            text="Exportar",
            command=self.exportar,
            state="disabled"
        )
        self.botao_exportar.pack(fill="x", pady=(14, 0))

        self.figura = Figure(figsize=(7.5, 4.5), dpi=100)
        self.eixo = self.figura.add_subplot(111)
        self.eixo.set_title("Dados de Identificação do Sistema")
        self.eixo.grid(True)
        self.canvas = FigureCanvasTkAgg(self.figura, master=corpo)
        self.canvas.get_tk_widget().pack(side="left", fill="both", expand=True)

    def escolher_arquivo(self):
        caminho = filedialog.askopenfilename(
            title="Escolher dataset",
            initialdir=PASTA_DATASET,
            filetypes=[("Arquivo MATLAB", "*.mat"), ("Todos os arquivos", "*.*")],
        )
        if caminho:
            self.carregar(caminho)

    def carregar(self, caminho):
        self._ocupado(True)
        try:
            dataset = carregar_dataset(caminho)
            smith = identificar(dataset.tempo, dataset.entrada, dataset.saida, "smith")
            sundaresan = identificar(dataset.tempo, dataset.entrada, dataset.saida, "sundaresan")
            melhor = min((smith, sundaresan), key=lambda modelo: modelo.eqm)
            fino = ajuste_fino(dataset.tempo, dataset.entrada, dataset.saida, melhor)
        except ValueError as erro:
            self.status_var.set(f"✖ Dataset inválido: {erro}")
            messagebox.showerror("Dataset inválido", str(erro))
            return
        finally:
            self._ocupado(False)

        self.dataset = dataset
        self.modelos = {"Smith": smith, "Sundaresan": sundaresan, "Ajuste fino": fino}
        menor_eqm = min(self.modelos, key=lambda nome: self.modelos[nome].eqm)

        self.lista_metodos.config(values=list(self.modelos), state="readonly")
        self.metodo_var.set(menor_eqm)
        self.botao_exportar.config(state="normal")
        self.status_var.set(
            f"✔ {dataset.nome} válido. Menor EQM: {menor_eqm} "
            f"({self.modelos[menor_eqm].eqm:.3f} {dataset.unidade})."
        )
        self.selecionar()

    def _ocupado(self, ocupado):
        self.canvas.get_tk_widget().winfo_toplevel().config(cursor="watch" if ocupado else "")
        self.canvas.get_tk_widget().update_idletasks()

    def selecionar(self):
        nome = self.metodo_var.get()
        modelo = self.modelos[nome]
        self.campos["k"].set(f"{modelo.k:.4f}")
        self.campos["tau"].set(f"{modelo.tau:.4f}")
        self.campos["theta"].set(f"{modelo.theta:.4f}")
        self.campos["eqm"].set(f"{modelo.eqm:.4f}")
        self.desenhar(nome)
        self.ao_selecionar(
            {"k": modelo.k, "tau": modelo.tau, "theta": modelo.theta}, nome, self.dataset
        )

    def desenhar(self, selecionado):
        dataset = self.dataset
        self.eixo.clear()
        self.eixo.plot(dataset.tempo, dataset.saida, color="0.55", lw=1, label="Resposta real")
        for nome, modelo in self.modelos.items():
            self.eixo.plot(
                dataset.tempo, modelo.yest, ESTILOS[nome],
                lw=2.4 if nome == selecionado else 1.1,
                alpha=1.0 if nome == selecionado else 0.6,
                label=f"{nome} (EQM={modelo.eqm:.3f})",
            )
        self.eixo.set_xlabel("Tempo (s)")
        self.eixo.set_ylabel(f"Velocidade ({dataset.unidade})" if dataset.unidade else "Amplitude")
        self.eixo.set_title(dataset.descricao or "Dados de Identificação do Sistema", fontsize=10)
        self.eixo.grid(True)
        self.eixo.legend(loc="lower right")
        self.figura.tight_layout()
        self.canvas.draw()

    def exportar(self):
        caminho = filedialog.asksaveasfilename(
            title="Exportar gráfico da identificação",
            defaultextension=".png",
            initialfile="identificacao.png",
            filetypes=[("Imagem PNG", "*.png"), ("PDF", "*.pdf"), ("SVG", "*.svg")],
        )
        if not caminho:
            return
        try:
            self.figura.savefig(caminho, dpi=300)
            messagebox.showinfo("Exportação concluída", f"Gráfico salvo em:\n{caminho}")
        except OSError as erro:
            messagebox.showerror("Erro ao exportar", str(erro))

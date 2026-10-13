import sys; sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.io import loadmat

RAIZ = Path(__file__).resolve().parents[1]
CAMINHO_DATASET = RAIZ / "dataset" / "Motor_G2.mat"
CAMINHO_FIGURA = RAIZ / "figuras" / "curva_reacao.png"

# %% Carregar dataset
dados = loadmat(CAMINHO_DATASET)
tempo = dados["t"].ravel()
acionamento = dados["Degrau"].ravel()
velocidade = dados["Saida"].ravel()

# %% Características do ensaio, calculadas a partir dos dados
i_degrau = int(np.argmax(acionamento != acionamento[0]))  # primeira amostra em que o degrau muda
t_degrau = tempo[i_degrau]
u_inicial, u_final = acionamento[0], acionamento[-1]
n_final = max(1, len(velocidade) // 10)  # 10% finais
y_inicial = velocidade[:i_degrau].mean()
y_final = velocidade[-n_final:].mean()
n_amostras = len(tempo)
duracao = tempo[-1] - tempo[0]
passo = np.median(np.diff(tempo))

print(f"Instante do degrau  : t = {t_degrau:.2f} s (amostra {i_degrau})")
print(f"Acionamento         : {u_inicial:.1f}% → {u_final:.1f}% (Δu = {u_final - u_inicial:.1f}%)")
print(f"Velocidade inicial  : {y_inicial:.2f} RPM (média antes do degrau)")
print(f"Velocidade final    : {y_final:.2f} RPM (média dos 10% finais)")
print(f"Amostras            : {n_amostras}")
print(f"Duração             : {duracao:.1f} s")
print(f"Passo de amostragem : {passo:.3f} s")

# %% Figura
figura, eixo_y = plt.subplots(figsize=(8, 5))
eixo_u = eixo_y.twinx()

linha_y, = eixo_y.plot(tempo, velocidade, "k", lw=1, label="Velocidade")
linha_u, = eixo_u.step(tempo, acionamento, where="post", color="tab:orange", lw=1.5,
                       label="Acionamento")

eixo_y.set_xlabel("Tempo (s)")
eixo_y.set_ylabel("Velocidade (RPM)")
eixo_u.set_ylabel("Acionamento (%)", color="tab:orange")
eixo_u.tick_params(axis="y", colors="tab:orange")

# Limites com o zero na mesma altura nos dois eixos (100/2100 = 5/105)
eixo_y.set_ylim(-100, 2000)
eixo_u.set_ylim(-5, 100)

eixo_y.set_title("Ensaio da curva de reação – Motor_G2")
eixo_y.grid(True)

# Degrau: seta no topo do degrau, texto acima da linha laranja e antes da subida da velocidade
eixo_u.annotate(
    f"degrau {u_inicial:.0f} → {u_final:.0f}% em t = {t_degrau:.0f} s",
    xy=(t_degrau, u_final), xytext=(t_degrau + 0.08 * duracao, u_final + 11),
    arrowprops=dict(arrowstyle="->"), va="center",
)

# Regime permanente: texto entre a curva preta e o topo do gráfico, longe da linha laranja
t_regime = tempo[0] + 0.85 * duracao
eixo_y.annotate(
    f"≈ {round(y_final, -1):.0f} RPM",
    xy=(t_regime, y_final), xytext=(t_regime - 0.2 * duracao, y_final + 125),
    arrowprops=dict(arrowstyle="->"), va="center",
)

eixo_y.legend([linha_y, linha_u], [linha_y.get_label(), linha_u.get_label()], loc="center right")

figura.tight_layout()
CAMINHO_FIGURA.parent.mkdir(exist_ok=True)
figura.savefig(CAMINHO_FIGURA, dpi=300)
print(f"\nFigura salva em: {CAMINHO_FIGURA.relative_to(RAIZ)}")
plt.show()

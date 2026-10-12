import json
import sys
from pathlib import Path
import matplotlib.pyplot as plt

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))  # permite rodar o arquivo direto, além de python -m

from identificação.identificacao import carregar_dataset, identificar, ajuste_fino
sys.stdout.reconfigure(encoding="utf-8")

PASTA_FIGURAS = RAIZ / "figuras"

# %% Carregar dataset
dataset = carregar_dataset(RAIZ / "dataset" / "Motor_G2.mat")
tempo, entrada, saida = dataset.tempo, dataset.entrada, dataset.saida
PASTA_FIGURAS.mkdir(exist_ok=True)

# %% Identificação
smith = identificar(tempo, entrada, saida, "smith")
sund = identificar(tempo, entrada, saida, "sundaresan")

print(f"{'Método':<12}{'k':>10}{'tau':>10}{'theta':>10}{'θ/τ':>8}{'EQM':>10}")
for m in (smith, sund):
    print(f"{m.metodo:<12}{m.k:>10.4f}{m.tau:>10.4f}{m.theta:>10.4f}{m.fator:>8.3f}{m.eqm:>10.4f}")

melhor = min((smith, sund), key=lambda m: m.eqm)
print(f"\nMelhor método: {melhor.metodo} (EQM = {melhor.eqm:.4f})")

# %% Comparação
plt.figure(figsize=(8, 5))
plt.plot(tempo, saida, "k", lw=1.2, label="Real")
plt.plot(tempo, smith.yest, "r--", lw=1.2, label=f"Smith (EQM={smith.eqm:.3f})")
plt.plot(tempo, sund.yest, "b-.", lw=1.2, label=f"Sundaresan (EQM={sund.eqm:.3f})")
plt.xlabel("Tempo (s)"); plt.ylabel(f"Velocidade ({dataset.unidade})")
plt.title("Resposta real x modelos identificados")
plt.grid(True); plt.legend(loc="lower right"); plt.tight_layout()
plt.savefig(PASTA_FIGURAS / "identificacao.png", dpi=300)

# %% Ajuste fino
fino = ajuste_fino(tempo, entrada, saida, melhor)
print(f"Ajuste fino: k={fino.k:.4f}  tau={fino.tau:.4f}  theta={fino.theta:.4f}  EQM={fino.eqm:.4f}")

# Visão geral e zoom no início da resposta, onde a mudança de theta aparece
fig, (geral, zoom) = plt.subplots(1, 2, figsize=(12, 5), gridspec_kw={"width_ratios": [3, 2]})
for eixo in (geral, zoom):
    eixo.plot(tempo, saida, color="0.6", lw=1, label="Real")
    eixo.plot(tempo, melhor.yest, "r--", lw=1.4, label=f"{melhor.metodo.capitalize()} (EQM={melhor.eqm:.3f})")
    eixo.plot(tempo, fino.yest, "g", lw=1.4, label=f"Ajuste fino (EQM={fino.eqm:.3f})")
    eixo.set_xlabel("Tempo (s)"); eixo.grid(True)
geral.set_ylabel(f"Velocidade ({dataset.unidade})")
geral.set_title("Efeito do ajuste fino")
geral.legend(loc="lower right")
zoom.set_xlim(10, 22); zoom.set_ylim(-40, 700)
zoom.set_title(f"Zoom: θ {melhor.theta:.2f} s → {fino.theta:.2f} s, τ {melhor.tau:.2f} s → {fino.tau:.2f} s")
fig.tight_layout()
fig.savefig(PASTA_FIGURAS / "ajuste_fino.png", dpi=300)

# %% Salvar o modelo
modelo = {
    "metodo": melhor.metodo, "k": melhor.k, "tau": melhor.tau, "theta": melhor.theta,
    "eqm": melhor.eqm, "fator_incontrolabilidade": melhor.fator,
    "ajustado": {"k": fino.k, "tau": fino.tau, "theta": fino.theta, "eqm": fino.eqm},
}
with open(RAIZ / "identificação" / "modelo_identificado.json", "w", encoding="utf-8") as f:
    json.dump(modelo, f, indent=2, ensure_ascii=False)

plt.show()

import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from scipy.io import loadmat
from scipy.optimize import minimize
from identificação.identificacao import identificar, simular_fopdt, eqm
import sys
sys.stdout.reconfigure(encoding="utf-8")

# %% Carregar dataset 
dados = loadmat("dataset/Motor_G2.mat")
tempo = dados["t"].ravel()
entrada = dados["Degrau"].ravel()
saida = dados["Saida"].ravel()
Path("figuras").mkdir(exist_ok=True)

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
plt.xlabel("Tempo (s)"); plt.ylabel("Velocidade (RPM)")
plt.title("Resposta real x modelos identificados")
plt.grid(True); plt.legend(loc="lower right"); plt.tight_layout()
plt.savefig("figuras/identificacao.png", dpi=300)

# %% Ajuste fino
def custo(p):
    k, tau, theta = p[0], abs(p[1]), abs(p[2])
    return eqm(simular_fopdt(k, tau, theta, tempo, entrada, melhor.u0, melhor.y0), saida)

res = minimize(custo, [melhor.k, melhor.tau, melhor.theta], method="Nelder-Mead")
k_aj, tau_aj, theta_aj = res.x[0], abs(res.x[1]), abs(res.x[2])
print(f"Ajuste fino: k={k_aj:.4f}  tau={tau_aj:.4f}  theta={theta_aj:.4f}  EQM={res.fun:.4f}")

plt.figure(figsize=(8, 5))
plt.plot(tempo, saida, "k", lw=1.2, label="Real")
plt.plot(tempo, melhor.yest, "r--", lw=1.2, label=f"{melhor.metodo} (EQM={melhor.eqm:.3f})")
plt.plot(tempo, simular_fopdt(k_aj, tau_aj, theta_aj, tempo, entrada, melhor.u0, melhor.y0),
         "g", lw=1.2, label=f"Ajuste fino (EQM={res.fun:.3f})")
plt.xlabel("Tempo (s)"); plt.ylabel("Velocidade (RPM)")
plt.title("Efeito do ajuste fino")
plt.grid(True); plt.legend(loc="lower right"); plt.tight_layout()
plt.savefig("figuras/ajuste_fino.png", dpi=300)

# %% Salvar o modelo 
modelo = {
    "metodo": melhor.metodo, "k": melhor.k, "tau": melhor.tau, "theta": melhor.theta,
    "eqm": melhor.eqm, "fator_incontrolabilidade": melhor.fator,
    "ajustado": {"k": k_aj, "tau": tau_aj, "theta": theta_aj, "eqm": float(res.fun)},
}
with open("identificação/modelo_identificado.json", "w", encoding="utf-8") as f:
    json.dump(modelo, f, indent=2, ensure_ascii=False)

plt.show()
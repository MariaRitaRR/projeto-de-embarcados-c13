import sys
from pathlib import Path

import control as ct
import matplotlib.pyplot as plt
import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))  # permite rodar o arquivo direto, além de python -m

from controle.malha_fechada import (
    CARGA_PADRAO,
    SETPOINT_PADRAO,
    carregar_modelo,
    planta_fopdt,
    simular_degrau_carga,
)
from identificação.sintonia_cohen_coon import cohen_coon
from identificação.sintonia_ziegler_nichols import ziegler_nichols

T_CARGA = 100.0  # s, depois da acomodação dos PIDs (~23 s) e da malha aberta (~81 s)
CAMINHO_FIGURA = RAIZ / "figuras" / "degrau_carga.png"


def malha_aberta_com_carga(modelo, t):
    # Acionamento fixo em SP/k: a carga derruba a velocidade e nada a corrige
    planta = planta_fopdt(modelo["k"], modelo["tau"], modelo["theta"])
    u = SETPOINT_PADRAO / modelo["k"] - np.where(t >= T_CARGA, CARGA_PADRAO, 0.0)
    _, y = ct.forced_response(planta, T=t, U=u)
    return np.asarray(y).ravel()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    modelo = carregar_modelo()
    k, tau, theta = modelo["k"], modelo["tau"], modelo["theta"]

    resultados = {}
    for nome, sintonia in (("Ziegler-Nichols", ziegler_nichols), ("Cohen-Coon", cohen_coon)):
        p = sintonia(k, tau, theta)
        resultados[nome] = simular_degrau_carga(p.kp, p.ti, p.td, carga=CARGA_PADRAO,
                                                t_carga=T_CARGA, modelo=modelo)

    t = resultados["Ziegler-Nichols"][0]
    y_aberta = malha_aberta_com_carga(modelo, t)

    print(f"Degrau de carga de {CARGA_PADRAO:.0f}% do acionamento em t = {T_CARGA:.0f} s "
          f"(SetPoint {SETPOINT_PADRAO:.0f} RPM)\n")
    print(f"{'Resposta':<18}{'queda (RPM)':>13}{'vale em (s)':>13}{'recuperação (s)':>17}{'erro final (RPM)':>18}")
    for nome, (_, y, m) in resultados.items():
        print(f"{nome:<18}{m['queda_carga']:>13.1f}{m['tempo_vale']:>13.2f}"
              f"{m['tempo_recuperacao']:>17.2f}{abs(SETPOINT_PADRAO - y[-1]):>18.1f}")
    print(f"{'Malha aberta':<18}{SETPOINT_PADRAO - y_aberta[-1]:>13.1f}{'-':>13}{'não recupera':>17}"
          f"{SETPOINT_PADRAO - y_aberta[-1]:>18.1f}")

    figura, (geral, zoom) = plt.subplots(1, 2, figsize=(12, 5), gridspec_kw={"width_ratios": [3, 2]})
    for eixo in (geral, zoom):
        eixo.plot(t, y_aberta, "k--", lw=1.2, label="Malha aberta")
        for nome, (t_r, y_r, _) in resultados.items():
            eixo.plot(t_r, y_r, lw=1.4, label=nome)
        eixo.axhline(SETPOINT_PADRAO, color="r", ls=":", lw=1, label=f"SetPoint ({SETPOINT_PADRAO:.0f} RPM)")
        eixo.axvline(T_CARGA, color="0.5", lw=1)
        eixo.set_xlabel("Tempo (s)")
        eixo.grid(True, alpha=0.4)
    geral.set_ylabel("Velocidade (RPM)")
    geral.set_title(f"Degrau de carga de {CARGA_PADRAO:.0f}% em t = {T_CARGA:.0f} s")
    geral.legend(loc="lower right")
    zoom.set_xlim(T_CARGA - 5, T_CARGA + 35)
    zoom.set_ylim(SETPOINT_PADRAO - 1.2 * k * CARGA_PADRAO, SETPOINT_PADRAO + 40)
    zoom.axhspan(0.98 * SETPOINT_PADRAO, 1.02 * SETPOINT_PADRAO, color="g", alpha=0.08, label="Faixa de 2%")
    zoom.set_title("Zoom na rejeição da carga")
    figura.tight_layout()

    CAMINHO_FIGURA.parent.mkdir(exist_ok=True)
    figura.savefig(CAMINHO_FIGURA, dpi=300)
    print(f"\nFigura salva em: {CAMINHO_FIGURA.relative_to(RAIZ)}")
    plt.show()


if __name__ == "__main__":
    main()

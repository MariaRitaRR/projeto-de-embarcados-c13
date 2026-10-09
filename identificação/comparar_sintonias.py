
import sys
from pathlib import Path

import matplotlib.pyplot as plt

from identificação.sintonia_cohen_coon import cohen_coon
from controle.malha_fechada import (
    carregar_modelo,
    simular_malha_fechada,
    SETPOINT_PADRAO,
)

RAIZ = Path(__file__).resolve().parents[1]
PASTA_FIGURAS = RAIZ / "figuras"


def ziegler_nichols(k, tau, theta):
    kp = 1.2 * tau / (k * theta)
    ti = 2 * theta
    td = 0.5 * theta
    return kp, ti, td


def imprimir_metricas(nome, metricas):
    print(f"\n{nome}")

    if not metricas["estavel"]:
        print(f"AVISO: {metricas['aviso']}")
        return

    print(f"Kp: {metricas['kp']:.6f}")
    print(f"Ti: {metricas['ti']:.6f} s")
    print(f"Td: {metricas['td']:.6f} s")
    print(f"Tempo de subida: {metricas['tempo_subida']:.3f} s")
    print(f"Tempo de acomodação: {metricas['tempo_acomodacao']:.3f} s")
    print(f"Overshoot: {metricas['overshoot']:.2f} %")
    print(f"Erro em regime: {metricas['erro_regime_pct']:.2f} %")


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    modelo = carregar_modelo(ajustado=True)
    k = modelo["k"]
    tau = modelo["tau"]
    theta = modelo["theta"]

    cc = cohen_coon(k, tau, theta)
    kp_zn, ti_zn, td_zn = ziegler_nichols(k, tau, theta)

    controladores = {
        "Cohen-Coon": (cc.kp, cc.ti, cc.td),
        "Ziegler-Nichols": (kp_zn, ti_zn, td_zn),
    }

    resultados = {}

    print("Modelo utilizado: parâmetros ajustados")
    print(f"K = {k:.6f}")
    print(f"tau = {tau:.6f} s")
    print(f"theta = {theta:.6f} s")
    print(f"theta/tau = {theta / tau:.4f}")

    for nome, (kp, ti, td) in controladores.items():
        t, y, metricas = simular_malha_fechada(
            kp,
            ti,
            td,
            setpoint=SETPOINT_PADRAO,
            modelo=modelo,
        )

        metricas["kp"] = kp
        metricas["ti"] = ti
        metricas["td"] = td

        imprimir_metricas(nome, metricas)
        resultados[nome] = (t, y, metricas)

    PASTA_FIGURAS.mkdir(exist_ok=True)

    plt.figure(figsize=(9, 5))

    for nome, (t, y, metricas) in resultados.items():
        if metricas["estavel"]:
            plt.plot(t, y, label=nome)

    plt.axhline(
        SETPOINT_PADRAO,
        color="black",
        linestyle="--",
        label="Setpoint (1800 RPM)",
    )

    plt.xlabel("Tempo (s)")
    plt.ylabel("Velocidade (RPM)")
    plt.title("Comparação dos controladores PID")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(
        PASTA_FIGURAS / "comparacao_sintonias.png",
        dpi=300,
    )
    plt.show()


if __name__ == "__main__":
    main()

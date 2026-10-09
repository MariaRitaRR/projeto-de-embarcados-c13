
import sys
from pathlib import Path

import matplotlib.pyplot as plt

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))  # permite rodar o arquivo direto, além de python -m

from identificação.sintonia_cohen_coon import cohen_coon
from identificação.sintonia_ziegler_nichols import ziegler_nichols
from controle.malha_fechada import (
    carregar_modelo,
    simular_malha_fechada,
    SETPOINT_PADRAO,
)

PASTA_FIGURAS = RAIZ / "figuras"


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
    zn = ziegler_nichols(k, tau, theta)

    controladores = {
        "Cohen-Coon": (cc.kp, cc.ti, cc.td),
        "Ziegler-Nichols": (zn.kp, zn.ti, zn.td),
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

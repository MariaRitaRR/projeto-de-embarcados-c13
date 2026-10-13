import sys
from pathlib import Path

import matplotlib.pyplot as plt

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from controle.malha_fechada import (
    GANHO_PADRAO,
    SETPOINT_PADRAO,
    carregar_modelo,
    simular_sem_controlador,
)

CAMINHO_FIGURA = RAIZ / "figuras" / "comparacao_malhas.png"


def main():
    modelo = carregar_modelo(ajustado=True)
    resultados = simular_sem_controlador(
        setpoint=SETPOINT_PADRAO,
        ganho=GANHO_PADRAO,
        modelo=modelo,
    )

    figura, eixo = plt.subplots(figsize=(9, 5))
    estilos = {"aberta": "tab:blue", "fechada": "tab:orange"}
    nomes = {"aberta": "Malha aberta", "fechada": "Malha fechada (K=0,2)"}

    print(f"Setpoint: {SETPOINT_PADRAO:.0f} RPM")
    print(f"Ganho da malha fechada: K = {GANHO_PADRAO:.2f}")
    print("\nResposta          tr (s)    ts (s)    erro (RPM)    erro (%)")

    for chave in ("aberta", "fechada"):
        tempo, resposta, metricas = resultados[chave]
        if not metricas["estavel"]:
            raise RuntimeError(metricas["aviso"])

        eixo.plot(tempo, resposta, color=estilos[chave], label=nomes[chave])
        print(
            f"{nomes[chave]:<19}"
            f"{metricas['tempo_subida']:>7.2f}"
            f"{metricas['tempo_acomodacao']:>10.2f}"
            f"{metricas['erro_regime']:>14.2f}"
            f"{metricas['erro_regime_pct']:>11.2f}"
        )

    eixo.axhline(
        SETPOINT_PADRAO,
        color="black",
        linestyle="--",
        linewidth=1,
        label=f"Setpoint ({SETPOINT_PADRAO:.0f} RPM)",
    )
    eixo.set_xlabel("Tempo (s)")
    eixo.set_ylabel("Velocidade (RPM)")
    eixo.set_title("Resposta do motor: malha aberta e malha fechada")
    eixo.grid(True, alpha=0.3)
    eixo.legend()
    figura.tight_layout()

    CAMINHO_FIGURA.parent.mkdir(exist_ok=True)
    figura.savefig(CAMINHO_FIGURA, dpi=300)
    print(f"\nFigura salva em: {CAMINHO_FIGURA.relative_to(RAIZ)}")
    plt.show()


if __name__ == "__main__":
    main()
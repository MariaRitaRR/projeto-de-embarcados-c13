import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # permite rodar o arquivo direto, além de python -m

from identificação.sintonia_cohen_coon import ParametrosPID


def ziegler_nichols(k: float, tau: float, theta: float) -> ParametrosPID:
    if k == 0 or tau <= 0 or theta <= 0:
        raise ValueError("Os parametros k, tau e theta devem ser validos.")

    kp = 1.2 * tau / (k * theta)
    ti = 2 * theta
    td = 0.5 * theta

    return ParametrosPID(kp=kp, ti=ti, td=td)


if __name__ == "__main__":
    with open(Path(__file__).with_name("modelo_identificado.json"), encoding="utf-8") as f:
        modelo = json.load(f)["ajustado"]
    k, tau, theta = modelo["k"], modelo["tau"], modelo["theta"]

    parametros = ziegler_nichols(k, tau, theta)

    print(f"theta/tau = {theta / tau:.4f}")
    print(f"Kp = {parametros.kp:.6f}")
    print(f"Ti = {parametros.ti:.6f} s")
    print(f"Td = {parametros.td:.6f} s")

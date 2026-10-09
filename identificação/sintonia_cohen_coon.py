import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ParametrosPID:
    kp: float
    ti: float
    td: float


def cohen_coon(k: float, tau: float, theta: float) -> ParametrosPID:
    if k == 0 or tau <= 0 or theta <= 0:
        raise ValueError("Os parametros k, tau e theta devem ser validos.")

    razao = theta / tau

    kp = (tau / (k * theta)) * ((16 * tau + 3 * theta) / (12 * tau))
    ti = theta * ((32 + 6 * razao) / (13 + 8 * razao))
    td = (4 * theta) / (11 + 2 * razao)

    return ParametrosPID(kp=kp, ti=ti, td=td)


if __name__ == "__main__":
    with open(Path(__file__).with_name("modelo_identificado.json"), encoding="utf-8") as f:
        modelo = json.load(f)["ajustado"]
    k, tau, theta = modelo["k"], modelo["tau"], modelo["theta"]

    parametros = cohen_coon(k, tau, theta)

    print(f"theta/tau = {theta / tau:.4f}")
    print(f"Kp = {parametros.kp:.6f}")
    print(f"Ti = {parametros.ti:.6f} s")
    print(f"Td = {parametros.td:.6f} s")
from dataclasses import dataclass


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
    k = 22.471578476721454
    tau = 19.85614984454135
    theta = 2.4673804124325507

    parametros = cohen_coon(k, tau, theta)

    print(f"theta/tau = {theta / tau:.4f}")
    print(f"Kp = {parametros.kp:.6f}")
    print(f"Ti = {parametros.ti:.6f} s")
    print(f"Td = {parametros.td:.6f} s")
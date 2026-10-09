from identificação.sintonia_cohen_coon import ParametrosPID


def ziegler_nichols(k: float, tau: float, theta: float) -> ParametrosPID:
    if k == 0 or tau <= 0 or theta <= 0:
        raise ValueError("Os parametros k, tau e theta devem ser validos.")

    kp = 1.2 * tau / (k * theta)
    ti = 2 * theta
    td = 0.5 * theta

    return ParametrosPID(kp=kp, ti=ti, td=td)

from dataclasses import dataclass, field
import numpy as np
from scipy import signal


@dataclass
class Modelo:
    metodo: str
    k: float
    tau: float
    theta: float
    eqm: float
    u0: float
    y0: float
    yest: np.ndarray = field(repr=False)

    @property
    def fator(self):
        return self.theta / self.tau


def simular_fopdt(k, tau, theta, tempo, entrada, u0, y0):
    t = tempo - tempo[0]
    u_atrasada = np.interp(t - theta, t, entrada - u0, left=0.0)
    _, y, _ = signal.lsim(([k], [tau, 1]), u_atrasada, t)
    return y + y0


def eqm(yest, saida):
    return float(np.sqrt(np.mean((yest - saida) ** 2)))


def _cruzamento(t, y, nivel):
    idx = np.argmax(y >= nivel)
    if y[idx] < nivel:
        raise ValueError(f"A resposta não atinge {100 * nivel:.1f}% do valor final.")
    if idx == 0:
        return t[0]
    return t[idx - 1] + (nivel - y[idx - 1]) * (t[idx] - t[idx - 1]) / (y[idx] - y[idx - 1])


def identificar(tempo, entrada, saida, metodo):
    tempo, entrada, saida = (np.asarray(v, dtype=float).ravel() for v in (tempo, entrada, saida))

    i0 = int(np.argmax(np.abs(entrada - entrada[0]) > 0))
    n_fim = max(1, len(saida) // 10)
    u0, u1 = entrada[0], entrada[-n_fim:].mean()
    y0 = saida[:max(i0, 1)].mean()
    y1 = saida[-n_fim:].mean()
    k = (y1 - y0) / (u1 - u0)

    tn = tempo[i0:] - tempo[i0]
    yn = (saida[i0:] - y0) / (y1 - y0)

    metodo = metodo.lower()
    if metodo == "smith":
        t1, t2 = _cruzamento(tn, yn, 0.283), _cruzamento(tn, yn, 0.632)
        tau = 1.5 * (t2 - t1)
        theta = t2 - tau
    elif metodo == "sundaresan":
        t1, t2 = _cruzamento(tn, yn, 0.353), _cruzamento(tn, yn, 0.853)
        tau = (2 / 3) * (t2 - t1)
        theta = 1.3 * t1 - 0.29 * t2
    else:
        raise ValueError("Método inválido: use 'smith' ou 'sundaresan'.")
    theta = max(theta, 0.0)

    yest = simular_fopdt(k, tau, theta, tempo, entrada, u0, y0)
    return Modelo(metodo, k, tau, theta, eqm(yest, saida), u0, y0, yest)
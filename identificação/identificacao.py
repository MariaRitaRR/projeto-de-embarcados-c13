from dataclasses import dataclass, field
from pathlib import Path
import numpy as np
from scipy import signal
from scipy.io import loadmat
from scipy.optimize import minimize

CHAVES_DATASET = ("t", "Degrau", "Saida")


@dataclass
class Dataset:
    nome: str
    tempo: np.ndarray = field(repr=False)
    entrada: np.ndarray = field(repr=False)
    saida: np.ndarray = field(repr=False)
    unidade: str
    descricao: str
    setpoint: float  # valor de referência do ensaio, usado como SetPoint inicial


def _texto(valor):
    if valor is None:
        return ""
    return str(np.asarray(valor).ravel()[0]) if np.size(valor) else ""


def _setpoint_do_ensaio(dados, saida):
    # Usa o valor alvo dos metadados quando existe; senão, o valor final medido no ensaio
    try:
        return float(np.asarray(dados["parametros"]["rpm_final"].item()).ravel()[0])
    except (KeyError, ValueError, IndexError, TypeError):
        return float(round(saida[-max(1, len(saida) // 10):].mean()))


def carregar_dataset(caminho):
    """Lê e valida um .mat de curva de reação; levanta ValueError explicando o problema."""
    caminho = Path(caminho)
    try:
        dados = loadmat(str(caminho))
    except Exception as erro:
        raise ValueError(f"Não foi possível ler {caminho.name}: {erro}") from None

    faltando = [chave for chave in CHAVES_DATASET if chave not in dados]
    if faltando:
        raise ValueError(f"{caminho.name} não tem as variáveis: {', '.join(faltando)}.")
    try:
        tempo, entrada, saida = (np.asarray(dados[c], dtype=float).ravel() for c in CHAVES_DATASET)
    except (TypeError, ValueError):
        raise ValueError("As variáveis t, Degrau e Saida devem ser numéricas.") from None

    if not len(tempo) == len(entrada) == len(saida):
        raise ValueError("t, Degrau e Saida devem ter o mesmo número de amostras.")
    if len(tempo) < 20:
        raise ValueError("O ensaio tem poucas amostras para identificar o processo.")
    if not all(np.all(np.isfinite(v)) for v in (tempo, entrada, saida)):
        raise ValueError("O ensaio contém valores inválidos (NaN ou infinito).")
    if np.any(np.diff(tempo) <= 0):
        raise ValueError("O vetor de tempo deve ser crescente.")
    if np.ptp(entrada) == 0:
        raise ValueError("A entrada não apresenta degrau.")

    return Dataset(caminho.name, tempo, entrada, saida, _texto(dados.get("unidade_saida")),
                   _texto(dados.get("descricao")), _setpoint_do_ensaio(dados, saida))


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


def ajuste_fino(tempo, entrada, saida, base):
    """Refina k, tau e theta do modelo `base` minimizando o EQM (Nelder-Mead)."""
    tempo, entrada, saida = (np.asarray(v, dtype=float).ravel() for v in (tempo, entrada, saida))

    def custo(p):
        return eqm(simular_fopdt(p[0], abs(p[1]), abs(p[2]), tempo, entrada, base.u0, base.y0), saida)

    res = minimize(custo, [base.k, base.tau, base.theta], method="Nelder-Mead")
    k, tau, theta = res.x[0], abs(res.x[1]), abs(res.x[2])
    yest = simular_fopdt(k, tau, theta, tempo, entrada, base.u0, base.y0)
    return Modelo("ajuste fino", k, tau, theta, float(res.fun), base.u0, base.y0, yest)
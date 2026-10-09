import json
import math
from pathlib import Path
import numpy as np
import control as ct
from scipy.optimize import brentq

RAIZ = Path(__file__).resolve().parents[1]
CAMINHO_MODELO = RAIZ / "identificação" / "modelo_identificado.json"
SETPOINT_PADRAO = 1800.0  # RPM, valor final do ensaio
ORDEM_PADE = 3
GANHO_PADRAO = 0.2  # K da malha fechada do item 4, ~1/3 do ganho crítico
N_PONTOS = 3000


def carregar_modelo(caminho=CAMINHO_MODELO, ajustado=True):
    """Lê k, tau e theta do JSON; usa o modelo do ajuste fino, ou o de Smith com ajustado=False."""
    with open(caminho, encoding="utf-8") as f:
        dados = json.load(f)
    if ajustado:
        dados = dados["ajustado"]
    return {"k": dados["k"], "tau": dados["tau"], "theta": dados["theta"]}


def planta_fopdt(k, tau, theta, ordem_pade=ORDEM_PADE):
    """G(s) = k/(tau·s + 1) em série com a aproximação de Padé de e^(-theta·s)."""
    return ct.series(ct.tf(k, [tau, 1]), ct.tf(*ct.pade(theta, ordem_pade)))


def controlador_pid(kp, ti, td):
    if ti is not None and ti <= 0:
        raise ValueError("Ti deve ser positivo (use None para remover a ação integral).")
    if td < 0:
        raise ValueError("Td não pode ser negativo.")
    if ti is None or math.isinf(ti):
        return ct.tf([kp * td, kp], [1])
    return ct.tf([kp * td, kp, kp / ti], [1, 0])


def ganho_critico(modelo=None):
    # Calculado com o atraso exato: fase de G(jw) = -180° em atan(tau·w) + theta·w = pi
    modelo = modelo or carregar_modelo()
    k, tau, theta = modelo["k"], modelo["tau"], modelo["theta"]
    if theta == 0:
        return math.inf
    w180 = brentq(lambda w: math.atan(tau * w) + theta * w - math.pi,
                  math.pi / (2 * theta), math.pi / theta)
    return math.sqrt(1 + (tau * w180) ** 2) / k


def verificar_estabilidade(sistema):
    """Retorna (estável?, polos). Estável se todos os polos têm parte real negativa."""
    polos = ct.poles(sistema)
    return bool(np.all(np.real(polos) < 0)), polos


def _vetor_tempo(polos, tau, t_final):
    if t_final is None:
        sigma = np.min(np.abs(np.real(polos)))
        t_final = max(5 * tau, 8 / sigma)
    return np.linspace(0, t_final, N_PONTOS)


def _cruzamento(t, y, nivel):
    idx = int(np.argmax(y >= nivel))
    if y[idx] < nivel:
        return math.nan
    if idx == 0:
        return t[0]
    return t[idx - 1] + (nivel - y[idx - 1]) * (t[idx] - t[idx - 1]) / (y[idx] - y[idx - 1])


def calcular_metricas(t, y, setpoint, valor_final):
    t10 = _cruzamento(t, y, 0.1 * valor_final)
    t90 = _cruzamento(t, y, 0.9 * valor_final)

    fora = np.flatnonzero(np.abs(y - valor_final) > 0.02 * abs(valor_final))
    if len(fora) == 0:
        ts = t[0]
    elif fora[-1] == len(y) - 1:
        ts = math.nan
    else:
        ts = t[fora[-1] + 1]

    i_pico = int(np.argmax(y))
    erro = setpoint - valor_final
    return {
        "valor_final": float(valor_final),
        "tempo_subida": float(t90 - t10),
        "tempo_10": float(t10),
        "tempo_90": float(t90),
        "tempo_acomodacao": float(ts),
        "overshoot": float(max(0.0, (y[i_pico] - valor_final) / valor_final * 100)),
        "pico": float(y[i_pico]),
        "tempo_pico": float(t[i_pico]),
        "erro_regime": float(erro),
        "erro_regime_pct": float(erro / setpoint * 100),
    }


def _simular(sistema, amplitude, setpoint, t):
    _, y = ct.step_response(sistema, T=t)
    y = amplitude * np.asarray(y).ravel()
    valor_final = amplitude * float(np.real(ct.dcgain(sistema)))
    metricas = calcular_metricas(t, y, setpoint, valor_final)
    metricas["aviso"] = None
    if math.isnan(metricas["tempo_acomodacao"]):
        metricas["aviso"] = (f"A resposta não acomodou em 2% dentro de {t[-1]:.1f} s; "
                             "aumente t_final.")
    return y, metricas


def _metricas_instavel(polos, aviso):
    chaves = ("valor_final", "tempo_subida", "tempo_10", "tempo_90", "tempo_acomodacao",
              "overshoot", "pico", "tempo_pico", "erro_regime", "erro_regime_pct")
    return {"estavel": False, "aviso": aviso, "polos": polos, **dict.fromkeys(chaves, math.nan)}


def simular_malha_fechada(kp, ti, td, setpoint=SETPOINT_PADRAO, modelo=None,
                          ordem_pade=ORDEM_PADE, t_final=None):
    modelo = modelo or carregar_modelo()
    planta = planta_fopdt(modelo["k"], modelo["tau"], modelo["theta"], ordem_pade)
    sistema = ct.feedback(ct.series(controlador_pid(kp, ti, td), planta), 1)

    estavel, polos = verificar_estabilidade(sistema)
    if not estavel:
        instaveis = ", ".join(f"{p:.3g}" for p in polos[np.real(polos) >= 0])
        aviso = (f"Sistema instável com Kp={kp}, Ti={ti}, Td={td}: "
                 f"polos com parte real >= 0: {instaveis}.")
        return np.array([]), np.array([]), _metricas_instavel(polos, aviso)

    t = _vetor_tempo(polos, modelo["tau"], t_final)
    y, metricas = _simular(sistema, setpoint, setpoint, t)
    return t, y, {"estavel": True, "polos": polos, **metricas}


def simular_sem_controlador(setpoint=SETPOINT_PADRAO, ganho=GANHO_PADRAO, modelo=None,
                            ordem_pade=ORDEM_PADE, t_final=None):
    # Malha aberta: G(s) com degrau Δu = SP/k. Malha fechada: K·G/(1 + K·G) com degrau SP.
    if ganho <= 0:
        raise ValueError("O ganho K deve ser positivo.")
    modelo = modelo or carregar_modelo()
    planta = planta_fopdt(modelo["k"], modelo["tau"], modelo["theta"], ordem_pade)
    malhas = {"aberta": (planta, setpoint / modelo["k"]),
              "fechada": (ct.feedback(ganho * planta, 1), setpoint)}

    estabilidade = {nome: verificar_estabilidade(sis) for nome, (sis, _) in malhas.items()}
    polos_estaveis = [p for estavel, p in estabilidade.values() if estavel]
    t = _vetor_tempo(np.concatenate(polos_estaveis), modelo["tau"], t_final) if polos_estaveis else None

    resultado = {}
    for nome, (sistema, amplitude) in malhas.items():
        estavel, polos = estabilidade[nome]
        if not estavel:
            instaveis = ", ".join(f"{p:.3g}" for p in polos[np.real(polos) >= 0])
            aviso = (f"Malha {nome} instável com K={ganho} (ganho crítico = "
                     f"{ganho_critico(modelo):.3f}): polos com parte real >= 0: {instaveis}.")
            resultado[nome] = (np.array([]), np.array([]), _metricas_instavel(polos, aviso))
            continue
        y, metricas = _simular(sistema, amplitude, setpoint, t)
        resultado[nome] = (t, y, {"estavel": True, "polos": polos, **metricas})
    return resultado


if __name__ == "__main__":
    import sys
    import matplotlib.pyplot as plt
    sys.stdout.reconfigure(encoding="utf-8")

    def imprimir(titulo, m):
        print(f"\n{titulo}")
        if not m["estavel"] or m["aviso"]:
            print(f"  AVISO: {m['aviso']}")
        if not m["estavel"]:
            return
        print(f"  Valor final       : {m['valor_final']:.2f} RPM")
        print(f"  Tempo de subida   : {m['tempo_subida']:.2f} s")
        print(f"  Tempo acomodação  : {m['tempo_acomodacao']:.2f} s")
        print(f"  Overshoot         : {m['overshoot']:.2f} %")
        print(f"  Erro em regime    : {m['erro_regime']:.2f} RPM ({m['erro_regime_pct']:.2f} %)")

    modelo = carregar_modelo()
    print(f"Modelo: k={modelo['k']:.4f}  tau={modelo['tau']:.4f}  theta={modelo['theta']:.4f}")

    # Valores só para testar o módulo; os definitivos vêm da sintonia ZN e Cohen-Coon (item 5)
    kp, ti, td = 0.2, 20.0, 1.0
    t, y, m = simular_malha_fechada(kp, ti, td, modelo=modelo)
    imprimir(f"PID de teste (Kp={kp}, Ti={ti}, Td={td})", m)

    print(f"\nGanho crítico: Kcr = {ganho_critico(modelo):.4f}")
    sem = simular_sem_controlador(ganho=GANHO_PADRAO, modelo=modelo)
    imprimir("Malha aberta (Δu = SP/k)", sem["aberta"][2])
    imprimir(f"Malha fechada com ganho K = {GANHO_PADRAO}", sem["fechada"][2])

    _, _, m_inst = simular_malha_fechada(2.0, 5.0, 1.0, modelo=modelo)
    imprimir("Caso instável (Kp=2, Ti=5, Td=1)", m_inst)

    Path(RAIZ / "figuras").mkdir(exist_ok=True)
    plt.figure(figsize=(8, 5))
    plt.plot(t, y, "b", lw=1.4, label=f"PID (Kp={kp}, Ti={ti}, Td={td})")
    for nome, estilo, rotulo in (("aberta", "k--", "Malha aberta"),
                                 ("fechada", "g-.", f"Malha fechada (K = {GANHO_PADRAO})")):
        t_s, y_s, m_s = sem[nome]
        if m_s["estavel"]:
            plt.plot(t_s, y_s, estilo, lw=1.2, label=rotulo)
    plt.axhline(SETPOINT_PADRAO, color="r", ls=":", lw=1, label="SetPoint")
    plt.xlabel("Tempo (s)"); plt.ylabel("Velocidade (RPM)")
    plt.title("Simulação da malha com PID de teste")
    plt.grid(True); plt.legend(loc="lower right"); plt.tight_layout()
    plt.savefig(RAIZ / "figuras" / "simulacao_pid_teste.png", dpi=300)

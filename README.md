# Identificação de Processos e Sintonia de Controladores PID
**C13 - Sistemas Embarcados**
Projeto Prático 1

**Grupo 2** · Planta: **Motor CC (controle de velocidade)** 
            · Métodos de sintonia: **Ziegler-Nichols Malha Aberta** e **Cohen-Coon**
            · Critério de desempenho: **menor tempo de resposta**

## Proposta 

A aplicação identifica o modelo de um motor CC a partir de um ensaio de curva de reação (resposta ao degrau em malha aberta), sintoniza controladores PID por métodos clássicos e permite ao usuário testar a malha fechada em uma interface gráfica com login, seleção de método de sintonia, sintonia manual e métrica de desempenho (tempo de subida, tempo de acomodação e overshoot).

## Parte teórica

### 1. Funcionamento da planta

![Sistema de controle em malha fechada](figuras/malha_fechada.png)

*Figura 1: Sistema de controle em malha fechada. Fonte: FUENTES (2005).*

O motor CC é bastante usado em acionamentos de velocidade variável justamente pela facilidade de controlar sua rotação e seu torque (FUENTES, 2005). Ele é formado por uma parte fixa, o **estator**, que gera o fluxo magnético principal $\Phi$, e uma parte girante, a **armadura**, alimentada por escovas e comutador. A interação entre o campo do estator e a corrente da armadura produz o torque que gira o eixo, e o comutador garante que esse torque mantenha sempre o mesmo sentido.

Considerando excitação independente ou ímãs permanentes, o fluxo $\Phi$ é constante, e a velocidade passa a ser controlada pela tensão aplicada na armadura (FUENTES, 2005). Nessa condição, o motor pode ser resumido em duas relações:

$$T = K_t\,I_a \qquad\qquad E = K_e\,\omega$$

O torque é proporcional à corrente de armadura, e a **força contraeletromotriz** $E$ é proporcional à velocidade. É ela que faz a resposta se estabilizar: conforme o motor acelera, $E$ aumenta, a corrente e o torque diminuem, e a velocidade para de crescer quando o torque equilibra as perdas e a carga.

Incluindo a indutância da armadura $L_a$, a inércia $J$ e o atrito viscoso $b$, o modelo dinâmico do motor é de segunda ordem (OGATA, 2010):

$$\frac{\Omega(s)}{V_a(s)} = \frac{K_t}{(L_a s + R_a)(J s + b) + K_t K_e}$$

Um polo vem da parte elétrica ($L_a/R_a$) e o outro da parte mecânica ($J/b$). Como a constante elétrica é muito mais rápida, a dinâmica mecânica domina, e o motor pode ser aproximado por um modelo de **primeira ordem com atraso**:

$$G(s) = \frac{k}{\tau s + 1}\,e^{-\theta s}$$

O atraso $\theta$ não aparece nas equações ideais do motor. Em um sistema real, ele vem de fatores como o tempo de amostragem do controlador, a filtragem da medição e o atrito estático. Já a constante de tempo identificada, de cerca de 20 s, é alta para um motor pequeno, o que indica um motor acionando uma carga com bastante inércia.



## Simulação da malha (`controle/malha_fechada.py`)

Este módulo é o núcleo de simulação do projeto. Ele é usado no modo Manual da interface, na comparação entre malha aberta e fechada (item 4) e nas sintonias ZN e Cohen-Coon (item 5).

O módulo trabalha assim:
- **Planta:** modelo FOPDT lido de `identificação/modelo_identificado.json`, com o atraso aproximado por Padé de ordem 3.
- **Controlador:** PID na forma ideal da eq. (8) do enunciado, $PID(s) = K_p\left(1 + \frac{1}{T_i s} + T_d s\right)$, com realimentação unitária.
- **Saída:** as funções **não plotam nada**. Elas retornam o tempo, a resposta e um dicionário de métricas, para cada um montar o próprio gráfico ou a interface.

### Como usar

Instale as dependências e rode os scripts **a partir da pasta raiz** do projeto:

```bash
pip install -r requirements.txt
python controle/malha_fechada.py   # exemplo: imprime as métricas e salva figuras/simulacao_pid_teste.png
```

Em outro script, importe as funções assim:

```python
from controle.malha_fechada import simular_malha_fechada, simular_sem_controlador, ganho_critico
```

### Funções

| Função | O que faz | Retorno |
|---|---|---|
| `simular_malha_fechada(kp, ti, td, setpoint=1800)` | Malha fechada com PID e degrau de SetPoint | `(t, y, metricas)` |
| `simular_sem_controlador(setpoint=1800, ganho=0.2)` | Malha aberta (degrau Δu = SP/k) e malha fechada só com ganho K, no mesmo vetor de tempo | `{"aberta": (t, y, metricas), "fechada": (t, y, metricas)}` |
| `ganho_critico()` | Ganho crítico Kcr da planta, calculado com o atraso exato | `float` (≈ 0,58) |
| `carregar_modelo(ajustado=True)` | Lê k, τ e θ do JSON; por padrão usa o modelo do ajuste fino, e `ajustado=False` usa o de Smith | `{"k", "tau", "theta"}` |

Parâmetros opcionais que todas as funções de simulação aceitam:
- **`modelo=`**: dicionário de `carregar_modelo()`. Se não for passado, usa o modelo do ajuste fino, que tem o menor EQM e é o adotado pelo grupo em todas as partes.
- **`ordem_pade=3`**: ordem da aproximação de Padé.
- **`t_final=`**: duração da simulação. Se não for passado, é escolhida automaticamente.

### Métricas retornadas

| Chave | Significado |
|---|---|
| `estavel` | `True` se todos os polos da malha fechada têm parte real negativa |
| `aviso` | `None`, ou um texto explicando o problema (malha instável, resposta que não acomodou) |
| `valor_final` | Valor final em RPM, pelo Teorema do Valor Final |
| `tempo_subida` | Tempo de 10 % a 90 % do valor final (s) |
| `tempo_acomodacao` | Tempo para entrar e ficar na faixa de 2 % do valor final (s) |
| `overshoot` | Sobressinal em % do valor final |
| `pico`, `tempo_pico` | Valor máximo da resposta (RPM) e o instante em que ocorre (s) |
| `erro_regime`, `erro_regime_pct` | SetPoint − valor final, em RPM e em % |
| `polos` | Polos da malha |

### Exemplo: item 4 (malha aberta × malha fechada)

```python
import matplotlib.pyplot as plt
from controle.malha_fechada import simular_sem_controlador, ganho_critico

print(f"Kcr = {ganho_critico():.3f}")        # o K escolhido precisa ser menor que isso
res = simular_sem_controlador(ganho=0.2)

for nome in ("aberta", "fechada"):
    t, y, m = res[nome]
    if m["estavel"]:
        plt.plot(t, y, label=f"Malha {nome}")
        print(nome, m["tempo_subida"], m["tempo_acomodacao"], m["erro_regime"])
    else:
        print(m["aviso"])
```

A malha fechada leva um ganho **K** no caminho direto. Com K = 1, ela é instável, porque o ganho crítico da planta é ≈ 0,58. Com K = 0,2, ela é bem mais rápida que a malha aberta (tempo de subida de 3,5 s contra 43,9 s e acomodação de 13,5 s contra 80,7 s), mas para em ≈ 1473 RPM: sobra um erro em regime de ≈ 18 %, que só a ação integral do PID elimina.

### Exemplo: item 5 (PID sintonizado)

```python
from controle.malha_fechada import simular_malha_fechada

kp, ti, td = ...   # valores calculados pela sintonia (ZN ou Cohen-Coon)
t, y, m = simular_malha_fechada(kp, ti, td, setpoint=1800)

if m["estavel"]:
    print(m["tempo_subida"], m["tempo_acomodacao"], m["overshoot"])
else:
    print(m["aviso"])   # a interface pode mostrar esse texto direto
```

### Observações

- **Malha instável:** a simulação não é feita. `t` e `y` voltam vazios, as métricas voltam como `nan` e `metricas["aviso"]` explica o motivo.
- **Pico negativo no início:** com ação derivativa ($T_d > 0$), a resposta começa com um pico negativo em t = 0. Isso é efeito da combinação da derivada ideal com a aproximação de Padé, não do motor. No motor real, a saída ficaria parada durante o atraso θ.

## Referências

FUENTES, Rodrigo Cardozo. **Apostila de Automação Industrial**: capítulo 5 – Controle de Motores de Corrente Contínua. Santa Maria: Colégio Técnico Industrial de Santa Maria, Universidade Federal de Santa Maria, 2005.

OGATA, Katsuhiko. **Engenharia de Controle Moderno**. 5. ed. São Paulo: Pearson Prentice Hall, 2010.

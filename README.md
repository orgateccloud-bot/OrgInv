# OrgAudi · Auditoria de Ganho de Capital em Espólio

Sistema **OrgAudi** — ORGATEC CONTABILIDADE E AUDITORIA
Autor técnico: Warley Veloso · Versão 0.4.0

## O que é

Sistema de **auditoria** da apuração de IR sobre ganho de capital em
sucessão *causa mortis*. Apura o imposto correto de cada bem e aplica
**todos os benefícios legais cabíveis** — opção do Art. 23, fatores de
redução FR1/FR2, redução da Lei 7.713/88, verificação de isenções.

"Abatimento dentro das normas" significa exatamente isto: o sistema
aplica cada redução que a lei concede, sobre os fatos verdadeiros. Não
persegue um IR-alvo nem reclassifica operação para baixar imposto.

## Princípios de projeto

1. **Lacuna ≠ zero.** Dado ausente é pendência que bloqueia a conclusão,
   nunca um zero silencioso.
2. **Regime vem do fato, não da conveniência.** A classificação de uma
   operação (venda do espólio, cessão de direitos, transmissão a herdeiro)
   é determinada pelos fatos. O sistema não a escolhe pelo resultado.
3. **Todo valor tem origem.** Valores extraídos de documentos carregam a
   fonte. Divergências entre documentos viram conflito explícito, não
   escolha automática.
4. **O GCAP oficial prevalece.** O cálculo de FR1/FR2 é forte ponto de
   partida; o número final se confere contra o GCAP da RFB.

## Módulos

| Módulo | Função |
|---|---|
| `dominio` | Bem, Espolio, Herdeiro, Regime, OpcaoArt23 |
| `tributario` | alíquotas progressivas, alertas |
| `fatores_reducao` | FR1/FR2 (Lei 11.196/05) + redução Lei 7.713/88 |
| `classificador` | árvore de decisão de regime tributário |
| `motor` | apuração por regime, com fatores aplicados |
| `otimizador` | cenários legais por bem + recomendação |
| `isencoes` | verificação de elegibilidade a isenções |
| `ingestao` | extração de valores de PDF com rastreio de origem |
| `reconciliador` | detecção de divergências entre documentos |
| `relatorio` | relatório textual consolidado |
| `laudo_xlsx` | laudo em planilha (4 abas) |

## Uso

```bash
python tests/test_motor.py            # bateria de testes
python data/exemplo_relatorio.py      # relatório de demonstração
```

## Os quatro regimes

| Regime | Quando | Diferível? | FR1/FR2? |
|---|---|---|---|
| Transmissão a herdeiro | bem partilhado | sim (§2º) | na venda futura |
| Venda pelo espólio | espólio aliena a terceiro | não | sim, se imóvel |
| Cessão de direitos hereditários | herdeiros vendem antes da partilha | não | sim, se imóvel |
| Fora do monte | bem não integra a sucessão | — | — |

## Estado e pendências

- FR1/FR2 implementado e validado contra exemplo independente. A
  convenção de contagem de meses é parâmetro explícito (`fatores_reducao.
  CONVENCAO_CONTAGEM_MESES`) — ajustar para casar com o GCAP oficial.
- Isenções: verificação de elegibilidade implementada; aplicação depende
  de confirmação humana de requisitos.
- Ingestão de PDF: extrai valores com origem; **não** decide qual valor
  usar quando há divergência — isso é resolvido no reconciliador.
- Para rodar o caso real é necessário: (a) classificar o regime de cada
  bem a partir dos fatos; (b) o custo de aquisição na DIRPF do falecido.

## Aviso

Software de apoio à auditoria. Não substitui o juízo do contador e do
advogado responsáveis. A classificação de regime de cada bem, os valores
de custo e os fatores de redução devem ser validados — estes últimos
contra o programa GCAP oficial da RFB — antes de qualquer entrega.

# Fase 1: primeira amostra (PNCP × CNPJ × CEIS/CNEP)

> Documento **interno**, fase exploratória. Nada aqui é publicação. Tom do handoff §3: os itens marcados como
> **ponto de atenção** são indicadores para verificar, **não provam irregularidade**. Sócios aparecem só com o nome e a
> qualificação do QSA, sem nenhum fragmento de CPF.

## Fontes e datas de extração

| Fonte | O que foi usado | Extraído em | Bruto | Script |
|---|---|---|---|---|
| PNCP, API de consulta (`pncp.gov.br/api/consulta/v1/contratos`, `/contratacoes/publicacao`, `/atas`) e API do portal (`/api/pncp/v1/orgaos/{cnpj}/contratos/{ano}/{seq}/termos`, `/orgaos`, `/unidades`) | contratos de 59 CNPJs municipais publicados desde 2021; contratações de 2026 em `codigoMunicipioIbge=1501402`; atas; termos | 23/10/2026 (01h–06h UTC) | `raw/pncp/2026-10-23/` | `scripts/pncp_pull.py` |
| PNCP, busca do site (`pncp.gov.br/api/search/`) | contratos municipais de Belém (para descobrir órgãos e conferir a API) | 23/10/2026 | `raw/pncp/2026-10-23/search/` | `scripts/pncp_pull.py` |
| SICONFI / Tesouro (`apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo`) | RREO Anexos 01 e 02: 6º bimestre de 2024 e 2025, 4º bimestre de 2026 | 23/10/2026 | `raw/siconfi/2026-10-23/` | `scripts/completude.py` |
| CNPJ, dados abertos da Receita (Nextcloud `arquivos.receitafederal.gov.br`, pasta `2026-10`, publicada em 13/10/2026) | Empresas, Estabelecimentos, Sócios, Simples e tabelas de domínio, **filtrados** pelos fornecedores e órgãos | 23/10/2026 | não guardado (zips apagados após o filtro; log em `data/staging/cnpj/log.jsonl`) | `scripts/cnpj_filter.py` |
| CEIS e CNEP (CGU, download diário sem chave) | arquivos de 22/10/2026 | 23/10/2026 | `raw/cgu/2026-10-23/` | `scripts/cnpj_filter.py` |

Banco: `data/observatorio.duckdb` (fora do git). Tabelas: `orgaos`, `contratos`, `aditivos`, `contratacoes`, `atas`,
`empresas`, `estabelecimentos`, `socios`, `simples`, `cnaes`, `motivos`, `municipios`, `naturezas`, `paises`,
`qualificacoes`, `ceis`, `cnep`. As tabelas desta página saem de `scripts/fase1_amostra.py` e `scripts/completude.py`.

## Resumo

- **O PNCP de Belém é pequeno e concentrado.** Foram verificados 59 CNPJs de entidades municipais (15 da Fase 0, 12 achados
  no registro de órgãos e nas contratações de 2026 do PNCP, 32 achados na base CNPJ da Receita). **Só 15 têm algum contrato
  publicado**, e são os mesmos 15 da Fase 0: **441 registros de contrato** no total (2022–2026), todos tocando 2024–2026.
  A busca do site do PNCP devolve exatamente os mesmos 441, órgão por órgão: a API não está escondendo nada; o que falta
  não foi publicado.
- **Vigentes em 2026:** 337 registros, **R$ 1,157 bilhão em valor global** (R$ 728 milhões se o valor for distribuído pelos
  dias de vigência que caem em 2026). A SEMEC sozinha responde por 67% desse valor. Os 20 maiores fornecedores somam
  R$ 960 milhões (83%).
- **Completude: claramente incompleto.** Contra a despesa do SICONFI sem pessoal e sem dívida, os contratos do PNCP cobrem
  cerca de **0,6% em 2024, 8,5% em 2025 e no máximo 24% em jan–ago/2026**, e esse teto está inflado porque o valor global de
  contrato é limite (registro de preços, "sob demanda"), não execução. **Saúde quase não aparece:** R$ 965 milhões
  empenhados em jan–ago/2026 contra R$ 3,3 milhões em contratos vigentes da SESMA. Dos 59 CNPJs verificados, 44 não têm nenhum contrato no
  PNCP, entre eles a Câmara, o Fundo Municipal de Saúde, a SEINFRA e a Superintendência de Mobilidade.
- **CEIS/CNEP:** 19 fornecedores aparecem no CEIS (45 registros de sanção) e nenhum no CNEP. Em quase todos os casos a
  sanção é de outro ente e não alcança contratos com Belém. Detalhe na seção própria.
- **Qualidade do registro:** 95 registros do tipo "Outros" (quase todos da SEMEC) são, na verdade, termos aditivos, atas,
  rescisões e autorizações publicados como se fossem contratos. Somar tudo inflaria o valor em cerca de R$ 194 milhões; esta
  amostra separa os tipos (coluna `tipo_registro`) e não soma atas, rescisões, autorizações nem duplicatas.

### Método das somas

- **Valor:** `valor_global` informado no PNCP. Entram nas somas os registros de `tipo_registro` *contrato* e *termo
  aditivo* (o aditivo de prorrogação cobre um período novo), sem duplicata exata (mesmo órgão, fornecedor, valor e número).
  Ficam de fora: atas de registro de preço (repetem o valor do contrato que delas decorre), rescisões, termos de
  autorização e doação. Regra em `scripts/pncp_pull.py`, função `classificar_registros`.
- **"Vigente em 2026":** vigência (início–fim) que toca 01/01/2026–31/12/2026. **Pro rata:** valor global × dias de vigência
  dentro do período ÷ dias totais de vigência.
- **Valor global é teto, não pagamento.** Pagamento só no Portal da Transparência de Belém (inacessível daqui, ver
  `fontes/fontes.md`).
- Datas: PNCP, SICONFI, CEIS/CNEP e CNPJ extraídos em **23/10/2026**; base CNPJ de **outubro/2026** (Receita, 13/10/2026);
  CEIS/CNEP de **22/10/2026**; SICONFI até o **4º bimestre/2026** (agosto).

## Contagens (PNCP, extraído em 23/10/2026)

- Órgãos verificados no PNCP: 59; com contrato: 15
- Registros de contrato: 441 (no escopo 2024–2026: 441)
- Termos (endpoint /termos): 20; contratações municipais publicadas em 2026: 202

| Tipo de registro | Registros | Soma do valor global | Entra nas somas |
|---|---:|---:|---|
| contrato | 342 | R$ 1.073.972.389 | sim |
| termo_aditivo | 79 | R$ 137.572.076 | sim |
| ata | 7 | R$ 171.899.431 | não |
| autorizacao | 7 | R$ 1.648.118 | não |
| rescisao | 5 | R$ 20.056.137 | não |
| doacao | 1 | R$ 2.700 | não |

Por ano de assinatura (só registros que entram nas somas):

| Ano | Registros | Valor global |
|---|---:|---:|
| 2022 | 1 | R$ 120.000 |
| 2023 | 13 | R$ 6.128.773 |
| 2024 | 28 | R$ 29.452.450 |
| 2025 | 226 | R$ 624.017.437 |
| 2026 | 146 | R$ 551.573.886 |

Vigentes em 2026 (vigência toca 2026), por órgão:

| Órgão | CNPJ | Registros | Valor global | Pro rata 2026 |
|---|---|---:|---:|---:|
| BELEM SECRETARIA MUNICIPAL DE EDUCACAO E CULTURA | `05055033000152` | 140 | R$ 775.205.354 | R$ 522.994.826 |
| SECRETARIA MUNICIPAL DE SANEAMENTO | `04789822000154` | 25 | R$ 184.424.395 | R$ 127.607.405 |
| MUNICIPIO DE BELEM | `05055009000113` | 43 | R$ 84.883.709 | R$ 26.691.780 |
| SECRETARIA MUNICIPAL DE SEGURANCA, ORDEM PUBLICA E MOBILIDADE DE BELEM - SEGBEL | `59815458000141` | 30 | R$ 67.535.545 | R$ 36.023.247 |
| BELEM SECRETARIA MUNICIPAL DE FINANCAS | `05055025000106` | 10 | R$ 28.309.082 | R$ 6.249.214 |
| FUNDACAO PAPA JOAO XXIII | `05065644000181` | 11 | R$ 9.523.414 | R$ 3.927.190 |
| SESMA-SECRETARIA MUNICIPAL DE SAUDE E MEIO AMBIENTE | `07917818000112` | 12 | R$ 3.328.386 | R$ 2.097.801 |
| GUARDA MUNICIPAL DE BELEM | `49159407000155` | 40 | R$ 2.329.907 | R$ 1.718.374 |
| SECRETARIA MUNICIPAL DE COMUNICACAO - SECOM | `59693965000150` | 3 | R$ 626.927 | R$ 575.255 |
| MUNICIPIO DE BELEM | `05055009000628` | 4 | R$ 603.361 | R$ 92.122 |
| SECRETARIA MUNICIPAL DE ECONOMIA | `10245579000106` | 1 | R$ 180.370 | R$ 90.926 |
| INSTITUTO DE PREVIDENCIA DOS SERVIDORES PUBLICOS DO MUNICIPIO DE BELEM | `29331615000182` | 7 | R$ 154.144 | R$ 57.284 |
| SECRETARIA MUNICIPAL DA MULHER | `59870569000150` | 8 | R$ 142.947 | R$ 108.196 |
| SECRETARIA MUNIC.DE COORD.GERAL DO PLANEJAM.E GESTAO | `14700173000127` | 1 | R$ 38.033 | R$ 19.121 |
| SECRETARIA MUNICIPAL DE CONTROLE, INTEGRIDADE E TRANSPARENCIA - SECONT | `09551008000110` | 2 | R$ 1.897 | R$ 835 |
| **Total** | | **337** | **R$ 1.157.287.471** | **R$ 728.253.576** |

## Pontos de atenção (para verificar; nenhum deles prova irregularidade)

Cada item diz o que o dado mostra e o que ele **não** mostra. Fonte: PNCP e Receita, extraídos em 23/10/2026.

1. **Saúde praticamente fora do PNCP.** A função Saúde empenhou R$ 964,9 milhões em jan–ago/2026 (SICONFI, RREO Anexo 02,
   inclui pessoal), e os contratos vigentes da SESMA no PNCP somam R$ 3,3 milhões. A SESMA publicou 24 contratações em
   2026 (R$ 279,6 milhões estimados, R$ 3,4 milhões homologados) e o Fundo Municipal de Saúde (`11305777000180`) está no
   registro do PNCP sem nenhum contrato. *Não mostra* que os contratos não existem: parte da despesa de saúde é repasse
   SUS a prestadores credenciados, convênios e folha; o resto pode estar publicado só no Diário Oficial ou no Mural do TCM-PA.
2. **Câmara Municipal sem contratos no PNCP.** O site da própria Câmara exporta 9 contratos de 2026 (Fase 0); no PNCP, o
   CNPJ `05416029000172` tem 4 contratações publicadas em 2026 e nenhum contrato. *Não mostra* falta de publicação legal: a
   Câmara publica no próprio portal; mostra que o PNCP não basta para o Legislativo.
3. **Atas, aditivos e rescisões publicados como contrato.** 95 registros do tipo "Outros", quase todos da SEMEC, repetem o
   valor de contratos já publicados (por exemplo, a "32ª ATA" e o "Contrato 64" da mesma empresa, ambos R$ 65,9 milhões).
   Alguns aditivos de prorrogação aparecem com enquadramento "Lei 14.133, art. 75, V" nas contratações. *Não mostra*
   duplicidade de pagamento; é um problema de cadastro que distorce qualquer soma feita direto do PNCP.
4. **46 contratações de 2026 homologadas sem contrato no PNCP** (R$ 80,8 milhões homologados; as maiores do Município de
   Belém: ITSM R$ 17,4 milhões, construção civil R$ 17,3 milhões). *Não mostra* contratação sem contrato: registro de preço
   pode não gerar contrato, e o contrato pode ter sido publicado só no Diário.
5. **Termo aditivo publicado em nome de outra empresa.** O 1º termo aditivo do Contrato 039/2025-SEMEC (prorrogação por 12
   meses, R$ 41,35 milhões, [PNCP](https://pncp.gov.br/app/contratos/05055033000152/2026/19)) está em nome da **SOLAR BELEM SPE
   LTDA** (aberta em 23/06/2025), enquanto o contrato original de mesmo valor
   ([PNCP](https://pncp.gov.br/app/contratos/05055033000152/2025/41)) está em nome da **CGM MANUTENCAO ELETRICA LTDA.**, que é
   sócia da SPE; as duas têm o mesmo administrador no QSA. *Não mostra* irregularidade: pode ser cessão ou sub-rogação
   prevista no edital da ata (Consórcio PRODNORTE). Verificar no processo.
6. **Porte declarado × valor.** RICKMANN CONFECCOES LTDA aparece na Receita como **ME** (microempresa) e tem R$ 26,0 milhões
   em contratos vigentes em 2026 com a SEMEC (uniformes, adesão a ata). *Não mostra* incapacidade: o porte é autodeclarado e
   pode estar desatualizado; é o indicador "capacidade incompatível" do handoff §6.1, a conferir com faturamento e
   atestados.
7. **Concentração na SEMEC.** 67% do valor vigente em 2026 no PNCP é da SEMEC, e os 20 maiores fornecedores levam 83% do
   total. *Não mostra* concentração real do gasto: reflete sobretudo quem publica no PNCP (ver completude).
8. **Fornecedor com declaração de inidoneidade no CEIS.** Um fornecedor tem declaração de inidoneidade (Governo da Bahia,
   desde 29/03/2022, sem data final e com abrangência "sem informação") e um contrato com Belém assinado em 01/06/2026 de
   R$ 799. Ver tabela do CEIS. *Não mostra* impedimento: a abrangência e a vigência da sanção precisam ser conferidas no
   processo original.

## 20 maiores fornecedores (PJ), contratos vigentes em 2026

Ranking pelo valor global somado dos contratos e aditivos vigentes em 2026 (método acima). Fonte: PNCP (contratos) e Receita, base CNPJ 2026-10 (razão social, natureza, porte, capital, abertura, CNAE, QSA); MEI/Simples pelo arquivo Simples. Pessoas físicas contratadas (54 CPFs) ficam fora do ranking. Sócios: nome e qualificação do QSA, sem CPF.

### 1. TERRAPLENA LTDA — `14.698.658/0001-23`

- **Contratado (valor global, vigentes em 2026):** R$ 166.149.885 em 1 registro(s) · órgãos: SECRETARIA MUNICIPAL DE SANEAMENTO
- **Objetos (resumo, maiores primeiro):** Contratação de empresa especializada para prestação de serviços comuns de engenharia, para execução de serviços de pavimentação asfáltica, m
- **PNCP:** https://pncp.gov.br/app/contratos/04789822000154/2026/4
- **Receita:** Sociedade Empresária Limitada; porte demais; capital social R$ 60.000.000
- **Abertura:** 29/09/1986 · **CNAE principal:** 3811400 Coleta de resíduos não-perigosos · situação ativa · sede BELEM/PA
- **Sócios (QSA):** CARLOS RAIMUNDO ALBUQUERQUE NASCIMENTO (Sócio-Administrador, desde 29/12/1999); CARLOS RAIMUNDO ALBUQUERQUE NASCIMENTO JUNIOR (Sócio, desde 29/12/1999)

### 2. DAFMC  SOLUCOES, COMERCIO E SERVICOS LTDA — `28.917.603/0001-71`

- **Contratado (valor global, vigentes em 2026):** R$ 125.000.000 em 3 registro(s) · órgãos: BELEM SECRETARIA MUNICIPAL DE EDUCACAO E CULTURA
- **Objetos (resumo, maiores primeiro):** O objeto do presente instrumento é a contratação de empresa para, sob demanda, prestar serviços de manutenção, adequação e reforma em prédio | O objeto do presente Termo Aditivo é a prorrogação do prazo de vigência do Contrato n° 009/2025 – SEMEC por 03 (três) meses, contado do seu  | O objeto do presente Termo Aditivo é a prorrogação do prazo de vigência do Contrato n° 009/2025 – SEMEC por 09 (nove) meses, considerando a 
- **PNCP:** https://pncp.gov.br/app/contratos/05055033000152/2025/8 · https://pncp.gov.br/app/contratos/05055033000152/2025/87 · https://pncp.gov.br/app/contratos/05055033000152/2026/16
- **Receita:** Sociedade Empresária Limitada; porte demais; capital social R$ 17.000.000
- **Abertura:** 23/10/2017 · **CNAE principal:** 4399101 Administração de obras · situação ativa · sede NITEROI/RJ
- **Sócios (QSA):** PAULO VITOR PINHEIRO ALVES (Sócio-Administrador, desde 19/10/2023)

### 3. CONSORCIO AMBAR — `59.374.962/0001-53`

- **Contratado (valor global, vigentes em 2026):** R$ 83.835.183 em 2 registro(s) · órgãos: BELEM SECRETARIA MUNICIPAL DE EDUCACAO E CULTURA
- **Objetos (resumo, maiores primeiro):** Adesão à Ata de Registro de Preços nº 003/2025 cujo objeto é o Registro de Preços para futura e eventual Contratação de Empresa para prestaç | O objeto deste Termo Aditivo consiste na prorrogação do prazo de execução e de vigência do Contrato nº 038/2025-SEMEC pelo período de 12 (do
- **PNCP:** https://pncp.gov.br/app/contratos/05055033000152/2025/48 · https://pncp.gov.br/app/contratos/05055033000152/2025/91
- **Receita:** Consórcio de Sociedades; porte demais; capital social R$ 0
- **Abertura:** 10/02/2025 · **CNAE principal:** 4693100 Comércio atacadista de mercadorias em geral, sem predominância de alimentos ou de insumos agropecuários · situação ativa · sede BELO HORIZONTE/MG
- **Sócios (QSA):** AGORA CONSTRUCOES E EMPREENDIMENTOS LTDA (Sociedade Consorciada, desde 10/02/2025); ALDO MARTINS PRUDENCIO (Administrador, desde 10/02/2025); OFFICIUM COMERCIO E REPRESENTACAO LTDA (Sociedade Consorciada, desde 10/02/2025); VIWA CONSTRUTORA E SERVICOS LTDA (Sociedade Consorciada, desde 10/02/2025)

### 4. SOLIDA NUTRICAO LTDA — `13.874.676/0001-56`

- **Contratado (valor global, vigentes em 2026):** R$ 65.899.440 em 1 registro(s) · órgãos: BELEM SECRETARIA MUNICIPAL DE EDUCACAO E CULTURA
- **Objetos (resumo, maiores primeiro):** PREGÃO ELETRÔNICO SRP Nº 90014/2025-SEMEC (Ref. Processo nº 12759/2025-Semec), que tem por objeto “CONTRATAÇÃO DE EMPRESA (SÓLIDA NUTRIÇÃO L
- **PNCP:** https://pncp.gov.br/app/contratos/05055033000152/2025/79
- **Receita:** Sociedade Empresária Limitada; porte demais; capital social R$ 15.000.000
- **Abertura:** 29/06/2011 · **CNAE principal:** 5620101 Fornecimento de alimentos preparados preponderantemente para empresas · situação ativa · sede CAIEIRAS/SP
- **Sócios (QSA):** RODRIGO FABRICIO DE ARRUDA (Administrador, desde 16/09/2020); R.A. PARTICIPACOES LTDA (Sócio, desde 22/11/2024)

### 5. X MOLD LTDA — `05.206.031/0001-17`

- **Contratado (valor global, vigentes em 2026):** R$ 61.094.700 em 1 registro(s) · órgãos: BELEM SECRETARIA MUNICIPAL DE EDUCACAO E CULTURA
- **Objetos (resumo, maiores primeiro):** Contratação de empresa especializada para eventual fornecimento e instalação de revestimentos modulares esportivos, do tipo indoor (para amb
- **PNCP:** https://pncp.gov.br/app/contratos/05055033000152/2025/82
- **Receita:** Sociedade Empresária Limitada; porte demais; capital social R$ 37.671.000
- **Abertura:** 16/05/2002 · **CNAE principal:** 2866600 Fabricação de máquinas e equipamentos para a indústria do plástico, peças e acessórios · situação ativa · sede CAMACARI/BA
- **Sócios (QSA):** ABEL ANTONIO DOS SANTOS NETO (Administrador, desde 16/02/2024); EDBEL HOLDING LTDA (Sócio, desde 16/02/2024); EDUARDO PESSOA CAMPELLO (Administrador, desde 16/02/2024)

### 6. RC NUTRY ALIMENTACAO LTDA — `11.164.874/0001-09`

- **Contratado (valor global, vigentes em 2026):** R$ 44.400.000 em 1 registro(s) · órgãos: BELEM SECRETARIA MUNICIPAL DE EDUCACAO E CULTURA
- **Objetos (resumo, maiores primeiro):** PREGÃO ELETRÔNICO SRP Nº 90014/2025-SEMEC (Ref. Processo nº 12759/2025-Semec), que tem por objeto “CONTRATAÇÃO DE EMPRESA ( RC NUTRY ALIMENT
- **PNCP:** https://pncp.gov.br/app/contratos/05055033000152/2025/80
- **Receita:** Sociedade Empresária Limitada; porte demais; capital social R$ 10.000.000
- **Abertura:** 07/01/2009 · **CNAE principal:** 5620101 Fornecimento de alimentos preparados preponderantemente para empresas · situação ativa · sede SAO PAULO/SP
- **Sócios (QSA):** SPERO PARTICIPACOES S/A (Sócio, desde 07/06/2017); FRANCISCO JOSE COELHO FREITAS (Administrador, desde 01/11/2023)

### 7. SERVPRED SERVICOS PREDIAL E AMBIENTAL LTDA — `13.803.194/0001-05`

- **Contratado (valor global, vigentes em 2026):** R$ 44.025.894 em 1 registro(s) · órgãos: MUNICIPIO DE BELEM
- **Objetos (resumo, maiores primeiro):** Contratação de empresa especializada para a execução de serviços de infraestrutura urbana, compreendendo obras de drenagem profunda, revesti
- **PNCP:** https://pncp.gov.br/app/contratos/05055009000113/2026/23
- **Receita:** Sociedade Empresária Limitada; porte demais; capital social R$ 50.000.000
- **Abertura:** 20/04/2011 · **CNAE principal:** 4222701 Construção de redes de abastecimento de água, coleta de esgoto e construções correlatas, exceto obras de irrigação · situação ativa · sede BELEM/PA
- **Sócios (QSA):** WALDIR MAIA DE ALBUQUERQUE (Sócio-Administrador, desde 25/07/2024)

### 8. MAQMOVEIS INDUSTRIA E COMERCIO DE MOVEIS LTDA. — `54.826.367/0005-11`

- **Contratado (valor global, vigentes em 2026):** R$ 42.456.270 em 3 registro(s) · órgãos: BELEM SECRETARIA MUNICIPAL DE EDUCACAO E CULTURA
- **Objetos (resumo, maiores primeiro):** ADESÃO À ATA DE REGISTRO DE PREÇOS N° 2025/000005, DECORRENTE DO PREGÃO ELETRÔNICO SRP Nº 02/2025 – CONSÓRCIO INTERMUNICIPAL DA REGIÃO CENTR | O objeto do presente instrumento é a aquisição de mobiliários escolares, nas condições estabelecidas no Termo de Referência. | O objeto do presente Termo Aditivo é o acréscimo do quantitativo de itens na margem do percentual de 25% (vinte e cinco por cento) ao Contra
- **PNCP:** https://pncp.gov.br/app/contratos/05055033000152/2025/81 · https://pncp.gov.br/app/contratos/05055033000152/2025/46 · https://pncp.gov.br/app/contratos/05055033000152/2025/83
- **Receita:** Sociedade Empresária Limitada; porte demais; capital social R$ 53.090.000
- **Abertura:** 05/12/2012 · **CNAE principal:** 3102100 Fabricação de móveis com predominância de metal · situação ativa · sede PARAGOMINAS/PA
- **Sócios (QSA):** ROBERTO RICARDO DA COSTA (Sócio-Administrador, desde 17/07/1985)

### 9. SOLAR BELEM SPE LTDA — `61.402.212/0001-90`

- **Contratado (valor global, vigentes em 2026):** R$ 41.354.473 em 1 registro(s) · órgãos: BELEM SECRETARIA MUNICIPAL DE EDUCACAO E CULTURA
- **Objetos (resumo, maiores primeiro):** O objeto do presente Termo Aditivo é a prorrogação da vigência do Contrato n° 039/2025 – SEMEC por 12 (doze) meses, contado do seu respectiv
- **PNCP:** https://pncp.gov.br/app/contratos/05055033000152/2026/19
- **Receita:** Sociedade Empresária Limitada; porte demais; capital social R$ 2.000.000
- **Abertura:** 23/06/2025 · **CNAE principal:** 4221903 Manutenção de redes de distribuição de energia elétrica · situação ativa · sede BELEM/PA
- **Sócios (QSA):** CGM MANUTENCAO ELETRICA LTDA. (Sócio, desde 23/06/2025); CARLOS AUGUSTO COUTO DA SILVA (Administrador, desde 11/11/2025)

### 10. CGM MANUTENCAO ELETRICA LTDA. — `23.018.199/0001-80`

- **Contratado (valor global, vigentes em 2026):** R$ 41.354.473 em 1 registro(s) · órgãos: BELEM SECRETARIA MUNICIPAL DE EDUCACAO E CULTURA
- **Objetos (resumo, maiores primeiro):** O objeto do presente contrato consiste na Adesão à Ata de Registro de Preços n.° 009/2023, decorrente da Concorrência Eletrônica SRP n.° 003
- **PNCP:** https://pncp.gov.br/app/contratos/05055033000152/2025/41
- **Receita:** Sociedade Empresária Limitada; porte demais; capital social R$ 6.545.366
- **Abertura:** 07/08/2015 · **CNAE principal:** 4221903 Manutenção de redes de distribuição de energia elétrica · situação ativa · sede BELEM/PA
- **Sócios (QSA):** MARCELO AMARAL RAFFAELE (Sócio, desde 07/08/2015); CARLOS AUGUSTO COUTO DA SILVA (Sócio-Administrador, desde 26/02/2021)

### 11. ALFATECH DISTRIBUICAO LTDA — `22.149.857/0001-00`

- **Contratado (valor global, vigentes em 2026):** R$ 39.782.000 em 2 registro(s) · órgãos: BELEM SECRETARIA MUNICIPAL DE EDUCACAO E CULTURA
- **Objetos (resumo, maiores primeiro):** O objeto do presente contrato é a AQUISIÇÃO DE NOTEBOOKS DESTINADOS AOS DOCENTES DAS UNIDADES ESCOLARES DA REDE MUNICIPAL DE EDUCAÇÃO DE BEL | O objeto do presente Termo Aditivo é a substituição qualitativa de marca e modelo do item 01/1.3 do Contrato n° 046/2025 – SEMEC, conforme j
- **PNCP:** https://pncp.gov.br/app/contratos/05055033000152/2025/62 · https://pncp.gov.br/app/contratos/05055033000152/2026/6
- **Receita:** Sociedade Empresária Limitada; porte demais; capital social R$ 25.000.000
- **Abertura:** 27/03/2015 · **CNAE principal:** 4651601 Comércio atacadista de equipamentos de informática · situação ativa · sede PALMAS/TO
- **Sócios (QSA):** MAURILIO VITORINO LEITE DA SILVA FILHO (Sócio-Administrador, desde 23/06/2023)

### 12. BELEM RIO SEGURANCA LTDA — `17.433.496/0001-90`

- **Contratado (valor global, vigentes em 2026):** R$ 37.531.869 em 4 registro(s) · órgãos: SECRETARIA MUNICIPAL DE SANEAMENTO; MUNICIPIO DE BELEM; BELEM SECRETARIA MUNICIPAL DE EDUCACAO E CULTURA; SECRETARIA MUNICIPAL DE COMUNICACAO - SECOM
- **Objetos (resumo, maiores primeiro):** O presente Contrato vincula-se às regras dispostas no Edital de licitação n°. 90007-2025, PREGÃO ELETRÔNICO SRP N° 90007/2025-SEGEP da ATA D | PRESTAÇÃO DE SERVIÇOS DE VIGILÂNCIA PATRIMONIAL ARMADA E DESARMADA | CONTRATAÇÃO DE EMPRESA ESPECIALIZADA NA PRESTAÇÃO DE SERVIÇOS DE VIGILÂNCIA PATRIMONIAL ARMADA E DESARMADA.
- **PNCP:** https://pncp.gov.br/app/contratos/05055033000152/2026/10 · https://pncp.gov.br/app/contratos/04789822000154/2025/8 · https://pncp.gov.br/app/contratos/05055009000113/2026/12
- **Receita:** Sociedade Empresária Limitada; porte demais; capital social R$ 6.132.000
- **Abertura:** 18/01/2013 · **CNAE principal:** 8011101 Atividades de vigilância e segurança privada · situação ativa · sede BELEM/PA
- **Sócios (QSA):** VICTOR SOUZA FLEXA (Sócio-Administrador, desde 10/08/2016)

### 13. KAPA CAPITAL FACILITIES LTDA — `13.279.768/0001-98`

- **Contratado (valor global, vigentes em 2026):** R$ 30.288.855 em 7 registro(s) · órgãos: BELEM SECRETARIA MUNICIPAL DE EDUCACAO E CULTURA; BELEM SECRETARIA MUNICIPAL DE FINANCAS; SECRETARIA MUNICIPAL DE SEGURANCA, ORDEM PUBLICA E MOBILIDADE DE BELEM - SEGBEL; MUNICIPIO DE BELEM; SECRETARIA MUNICIPAL DA MULHER; SECRETARIA MUNICIPAL DE ECONOMIA
- **Objetos (resumo, maiores primeiro):** O presente Contrato vincula-se às regras dispostas no Edital de licitação n° 90008/2025 – SEGEP (Pregão Eletrônico), da Ata de Registro de P | O presente Contrato tem como objeto a “CONTRATAÇÃO DE EMPRESA ESPECIALIZADA NA PRESTAÇÃO DE SERVIÇO DE LIMPEZA E CONSERVAÇÃO, COM REGIME DE  | CONTRATAÇÃO DE EMPRESA ESPECIALIZADA NA PRESTAÇÃO DE SERVIÇO DE LIMPEZA E CONSERVAÇÃO, COM REGIME DE DEDICAÇÃO EXCLUSIVA DE MÃO-DE-OBRA E FO
- **PNCP:** https://pncp.gov.br/app/contratos/05055033000152/2026/3 · https://pncp.gov.br/app/contratos/59815458000141/2026/4 · https://pncp.gov.br/app/contratos/05055025000106/2026/1
- **Receita:** Sociedade Empresária Limitada; porte demais; capital social R$ 2.000.000
- **Abertura:** 17/02/2011 · **CNAE principal:** 7820500 Locação de mão-de-obra temporária · situação ativa · sede BELEM/PA
- **Sócios (QSA):** EDILEUSA MATOS E SILVA (Administrador, desde 28/10/2025); FIDELITY INVESTMENTS S A (Sócio, desde 28/10/2025)

### 14. COMPANHIA DE TRANSFORMACAO DIGITAL DO MUNICIPIO DE BELEM - BELEM DIGITAL — `04.850.095/0001-93`

- **Contratado (valor global, vigentes em 2026):** R$ 27.299.002 em 2 registro(s) · órgãos: BELEM SECRETARIA MUNICIPAL DE EDUCACAO E CULTURA; BELEM SECRETARIA MUNICIPAL DE FINANCAS
- **Objetos (resumo, maiores primeiro):** Fornecimento de Solução Integrada de Gestão de Tributos, incluindo licenças permanentes de softwares, serviços de customização e parametriza | O objeto do presente Termo Aditivo é a prorrogação do prazo de vigência do Contrato n° 085/2024 –SEMEC por mais 12 (doze) meses, no valor to
- **PNCP:** https://pncp.gov.br/app/contratos/05055025000106/2026/7 · https://pncp.gov.br/app/contratos/05055033000152/2024/29
- **Receita:** Sociedade de Economia Mista; porte demais; capital social R$ 8.248.612
- **Abertura:** 10/05/1983 · **CNAE principal:** 6311900 Tratamento de dados, provedores de serviços de aplicação e serviços de hospedagem na internet · situação ativa · sede BELEM/PA
- **Sócios (QSA):** HAROLDO ALENCAR DE SOUSA NETO (Diretor, desde 18/04/2023); FLAVIO AUGUSTO FERREIRA DA SILVA (Diretor, desde 21/01/2025); GUSTAVO BEZERRA DA COSTA (Presidente, desde 21/01/2025); ADRIANA NUNES TELES XISTO (Diretor, desde 21/01/2025)

### 15. RICKMANN CONFECCOES LTDA — `34.008.537/0001-10`

- **Contratado (valor global, vigentes em 2026):** R$ 26.029.201 em 2 registro(s) · órgãos: BELEM SECRETARIA MUNICIPAL DE EDUCACAO E CULTURA
- **Objetos (resumo, maiores primeiro):** O presente Contrato tem como objeto a Adesão à Ata de Registro de Preços n° 729/2025 – Processo SED 117383/2025 – SEA 21731/2025 - LOTE 01,  | O objeto do presente Termo Aditivo é a supressão total do item 55, LOTE 07, do Contrato n° 069/2025 – SEMEC, e a supressão de 1 (uma) unidad
- **PNCP:** https://pncp.gov.br/app/contratos/05055033000152/2025/85 · https://pncp.gov.br/app/contratos/05055033000152/2026/9
- **Receita:** Sociedade Empresária Limitada; porte ME; capital social R$ 2.000.000
- **Abertura:** 24/06/2019 · **CNAE principal:** 1412603 Facção de peças do vestuário, exceto roupas íntimas · situação ativa · sede GASPAR/SC
- **Sócios (QSA):** ELDO UMBELINO JUNIOR (Sócio-Administrador, desde 28/11/2024)

### 16. EQUATORIAL PARA DISTRIBUIDORA DE ENERGIA S.A. — `04.895.728/0001-80`

- **Contratado (valor global, vigentes em 2026):** R$ 20.631.250 em 3 registro(s) · órgãos: MUNICIPIO DE BELEM; BELEM SECRETARIA MUNICIPAL DE EDUCACAO E CULTURA
- **Objetos (resumo, maiores primeiro):** O objeto deste Termo Aditivo é a prorrogação do prazo de vigência por 12 (doze) meses e o acréscimo quantitativo na margem percentual de 25% | 1.1. O objeto do presente Termo Aditivo é promover a renomeação da Contratante de Secretaria Municipal de Educação para Secretaria Municipal | Prestação de Serviço Público de Energia Elétrica para unidades consumidoras do Grupo B, para atender a Guarda Municipal de Belém.
- **PNCP:** https://pncp.gov.br/app/contratos/05055033000152/2023/54 · https://pncp.gov.br/app/contratos/05055033000152/2023/33 · https://pncp.gov.br/app/contratos/05055009000628/2024/1
- **Receita:** Sociedade Anônima Aberta; porte demais; capital social R$ 1.633.752.316
- **Abertura:** 07/11/1969 · **CNAE principal:** 3514000 Distribuição de energia elétrica · situação ativa · sede BELEM/PA
- **Sócios (QSA):** AUGUSTO MIRANDA DA PAZ JUNIOR (Conselheiro de Administração, desde 07/05/2018); ARMANDO DE SOUZA NASCIMENTO (Conselheiro de Administração, desde 07/05/2018); FIRMINO FERREIRA SAMPAIO NETO (Conselheiro de Administração, desde 07/05/2018); MARCOS ANTONIO SOUZA DE ALMEIDA (Diretor, desde 04/06/2018); TATIANA QUEIROGA VASQUES (Diretor, desde 08/05/2019); MAURO CHAVES DE ALMEIDA (Conselheiro de Administração, desde 09/06/2021); MARCIO CAIRES VASCONCELOS (Presidente, desde 21/01/2023); JOAO ALBERTO DA SILVA NETO (Conselheiro de Administração, desde 20/05/2024); NIERBETH COSTA BRITO (Diretor, desde 20/01/2025); ANDRE LUIZ BARATA PESSOA (Diretor, desde 20/01/2025)

### 17. TEN TAVARES ENERGIA E CONSTRUTORA LTDA — `08.458.916/0001-00`

- **Contratado (valor global, vigentes em 2026):** R$ 20.023.514 em 1 registro(s) · órgãos: MUNICIPIO DE BELEM
- **Objetos (resumo, maiores primeiro):** Contratação de Empresa Especializada para Execução de Obras de Implantação de Praças e Urbanização de Espaços Públicos de Lazer no Município
- **PNCP:** https://pncp.gov.br/app/contratos/05055009000113/2026/17
- **Receita:** Sociedade Empresária Limitada; porte demais; capital social R$ 9.000.000
- **Abertura:** 14/11/2006 · **CNAE principal:** 4391600 Obras de fundações · situação ativa · sede BELEM/PA
- **Sócios (QSA):** JULIANA PINTO DE SOUZA CASTELO BRANCO MARTHA TAVARES (Sócio-Administrador, desde 01/06/2015)

### 18. CONCRETA ENGENHARIA LTDA — `09.120.837/0001-49`

- **Contratado (valor global, vigentes em 2026):** R$ 15.115.193 em 1 registro(s) · órgãos: SECRETARIA MUNICIPAL DE SANEAMENTO
- **Objetos (resumo, maiores primeiro):** Contratação de empresa especializada para prestação de serviços comuns de engenharia, destinados à execução de serviços de recapeamento e re
- **PNCP:** https://pncp.gov.br/app/contratos/04789822000154/2026/5
- **Receita:** Sociedade Empresária Limitada; porte demais; capital social R$ 10.000.000
- **Abertura:** 10/10/2007 · **CNAE principal:** 4211101 Construção de rodovias e ferrovias · situação ativa · sede MARABA/PA
- **Sócios (QSA):** JESSICA RIGO (Administrador, desde 28/08/2013); CONCRETA PARTICIPACOES LTDA (Sócio, desde 23/05/2025)

### 19. UNITY ONE SOLUCOES EM GESTAO TECNOLOGICA LTDA. — `18.110.055/0001-10`

- **Contratado (valor global, vigentes em 2026):** R$ 14.311.324 em 1 registro(s) · órgãos: SECRETARIA MUNICIPAL DE SEGURANCA, ORDEM PUBLICA E MOBILIDADE DE BELEM - SEGBEL
- **Objetos (resumo, maiores primeiro):** O objeto do presente instrumento é a Adesão à Ata de Registro de Preços nº 02/2024 – DETRAN - PA, cujo objeto é o registro de preços para a 
- **PNCP:** https://pncp.gov.br/app/contratos/59815458000141/2026/16
- **Receita:** Sociedade Empresária Limitada; porte demais; capital social R$ 5.100.000
- **Abertura:** 14/05/2013 · **CNAE principal:** 6209100 Suporte técnico, manutenção e outros serviços em tecnologia da informação · situação ativa · sede BELEM/PA
- **Sócios (QSA):** CAMILLA RUBIN MATOS (Sócio-Administrador, desde 05/08/2026)

### 20. COOPERATIVA DOS PRODUTORES AGROEXTRATIVISTAS E DOS BARQUEIROS DO PARA — `10.478.514/0001-00`

- **Contratado (valor global, vigentes em 2026):** R$ 13.528.011 em 2 registro(s) · órgãos: BELEM SECRETARIA MUNICIPAL DE EDUCACAO E CULTURA
- **Objetos (resumo, maiores primeiro):** O objeto do presente instrumento é a CONTRATAÇÃO EMERGENCIAL DE PESSOA JURÍDICA PARA PRESTAÇÃO DE SERVIÇOS DE TRANSPORTE FLUVIAL (BARCO A MO | O objeto do presente Termo Aditivo é a prorrogação por mais 12 (doze) meses do prazo de vigência do Contrato n° 003/2021-FUNBOSQUE, cujo obj
- **PNCP:** https://pncp.gov.br/app/contratos/05055033000152/2026/39 · https://pncp.gov.br/app/contratos/05055033000152/2025/63
- **Receita:** Cooperativa; porte demais; capital social R$ 7.140.000
- **Abertura:** 08/08/2008 · **CNAE principal:** 5021101 Transporte por navegação interior de carga, municipal, exceto travessia · situação ativa · sede BELEM/PA
- **Sócios (QSA):** EDSON MAGNO FARIAS DO NASCIMENTO (Presidente, desde 08/08/2008); JOAO PAULO AFONSO MORAES (Diretor, desde 01/03/2019); FRANCISCO RIBEIRO CAMPOS (Diretor, desde 29/12/2025); EDINEI NASCIMENTO DA SILVA (Diretor, desde 29/12/2025); LEIZIENE DOS PASSOS PEREIRA (Diretor, desde 29/12/2025)

## CEIS / CNEP (CGU, arquivos de 22/10/2026)

Casamento pelo CNPJ do fornecedor (14 dígitos) ou pela raiz (8 dígitos, outro estabelecimento da mesma empresa). A coluna *Contrato com Belém no período* diz se algum contrato com Belém foi **assinado** entre o início e o fim da sanção. Isso só seria impeditivo se a abrangência da sanção alcançasse o município (por exemplo, inidoneidade ou "todas as esferas"); impedimento "no órgão sancionador" ou "na esfera do sancionador" federal, estadual ou de outro município não impede contratar com Belém.

**CEIS** (arquivo de 20261022): 19 fornecedor(es), 45 registro(s) de sanção

| Fornecedor | CNPJ | Casa por | Contratos com Belém (valor) | Categoria | Início | Fim | Órgão sancionador | Abrangência | Contrato com Belém no período |
|---|---|---|---|---|---|---|---|---|---|
| ALEA COMERCIAL LTDA | `12011917000332` | raiz | 1 (R$ 3.981.907) | Suspensão | 07/02/2025 | 09/04/2025 | TRIBUNAL DE JUSTICA DA BAHIA (TJ-BA) (BA) | Na Esfera e no Poder do órgão sancionador | não |
| ANTONIA RAIMUNDA ALVES | `12560585000183` | CNPJ | 1 (R$ 1.370) | Impedimento/proibição de contratar com prazo determinado | 20/02/2025 | 20/02/2027 | Prefeitura Municipal de São Mateus do Sul (PR) (PR) | No órgão sancionador | **sim**: 08/05/2025 |
| ANTONIA RAIMUNDA ALVES | `12560585000183` | CNPJ | 1 (R$ 1.370) | Impedimento/proibição de contratar com prazo determinado | 30/07/2026 | 30/10/2026 | COMANDO DA AERONAUTICA (SP) | Em todos os Poderes da Esfera do órgão sancionador | não |
| ATENA COMERCIO COMPRA E VENDA LTDA | `42107381000152` | CNPJ | 1 (R$ 4.565) | Impedimento/proibição de contratar com prazo determinado | 02/10/2026 | 01/12/2026 | TRIBUNAL SUPERIOR DO TRABALHO TST (RJ) | Em todos os Poderes da Esfera do órgão sancionador | não |
| ATENA COMERCIO COMPRA E VENDA LTDA | `42107381000152` | CNPJ | 1 (R$ 4.565) | Impedimento/proibição de contratar com prazo determinado | 14/08/2026 | 13/02/2027 | UNIVERSIDADE TECNOLOGICA FEDERAL DO PARANA (PR) | Em todos os Poderes da Esfera do órgão sancionador | não |
| BRASIDAS LTDA | `20483193000196` | CNPJ | 1 (R$ 799) | Declaração de Inidoneidade com prazo determinado | 29/03/2022 | — | Governo do Estado da Bahia (BA) (BA) | Sem Informação | **sim**: 01/06/2026 |
| CINTIA SILVA DA COSTA | `26904546000160` | CNPJ | 1 (R$ 6.000) | Suspensão | 27/07/2026 | 27/07/2028 | Controladoria Geral do Estado de Rondônia - RO (RO) | Em todos os Poderes da Esfera do órgão sancionador | não |
| D DOS S VASQUES LTDA | `37356450000121` | CNPJ | 1 (R$ 13.000) | Impedimento/proibição de contratar com prazo determinado | 17/11/2025 | 17/04/2027 | AGENCIA NACIONAL DE VIGILANCIA SANITARIA (DF) | Em todos os Poderes da Esfera do órgão sancionador | não |
| DAVANTI MAQUINAS, MOVEIS E EQUIPAMENTOS INDUSTRIAIS LTDA | `44259236000112` | CNPJ | 1 (R$ 82.539) | Suspensão | 03/08/2026 | 03/08/2028 | PREFEITURA DE RIBEIRÃO PRETO (SP) | No órgão sancionador | não |
| DAVANTI MAQUINAS, MOVEIS E EQUIPAMENTOS INDUSTRIAIS LTDA | `44259236000112` | CNPJ | 1 (R$ 82.539) | Impedimento/proibição de contratar com prazo determinado | 06/03/2026 | 06/03/2027 | FUNDACAO OSWALDO CRUZ (RJ) | Em todos os Poderes da Esfera do órgão sancionador | não |
| DAVANTI MAQUINAS, MOVEIS E EQUIPAMENTOS INDUSTRIAIS LTDA | `44259236000112` | CNPJ | 1 (R$ 82.539) | Impedimento/proibição de contratar com prazo determinado | 07/05/2026 | 06/05/2027 | Prefeitura Municipal de Atibaia (SP) (SP) | Em todos os Poderes da Esfera do órgão sancionador | não |
| DAVANTI MAQUINAS, MOVEIS E EQUIPAMENTOS INDUSTRIAIS LTDA | `44259236000112` | CNPJ | 1 (R$ 82.539) | Impedimento/proibição de contratar com prazo determinado | 14/07/2026 | 14/07/2027 | COMANDO DA MARINHA (RJ) | Em todos os Poderes da Esfera do órgão sancionador | não |
| DAVANTI MAQUINAS, MOVEIS E EQUIPAMENTOS INDUSTRIAIS LTDA | `44259236000112` | CNPJ | 1 (R$ 82.539) | Impedimento/proibição de contratar com prazo determinado | 15/12/2025 | 15/12/2026 | PREFEITURA DE DOIS VIZINHOS - PR (PR) | Em todos os Poderes da Esfera do órgão sancionador | não |
| DAVANTI MAQUINAS, MOVEIS E EQUIPAMENTOS INDUSTRIAIS LTDA | `44259236000112` | CNPJ | 1 (R$ 82.539) | Impedimento/proibição de contratar com prazo determinado | 16/05/2025 | 16/05/2027 | PREFEITURA MUNICIPAL DE CAMPO BELO-MG (MG) | Em todos os Poderes da Esfera do órgão sancionador | **sim**: 02/06/2025 |
| DAVANTI MAQUINAS, MOVEIS E EQUIPAMENTOS INDUSTRIAIS LTDA | `44259236000112` | CNPJ | 1 (R$ 82.539) | Impedimento/proibição de contratar com prazo determinado | 23/12/2025 | 23/12/2026 | Governo do Estado do Rio Grande do Sul (RS) (RS) | Em todos os Poderes da Esfera do órgão sancionador | não |
| IBBA INDUSTRIA E COMERCIO DE BEBEDOURO LTDA | `50456480000178` | CNPJ | 1 (R$ 310.100) | Impedimento/proibição de contratar com prazo determinado | 15/05/2026 | 16/11/2026 | UNIVERSIDADE FEDERAL DO PARA (PA) | Em todos os Poderes da Esfera do órgão sancionador | não |
| IBBA INDUSTRIA E COMERCIO DE BEBEDOURO LTDA | `50456480000178` | CNPJ | 1 (R$ 310.100) | Impedimento/proibição de contratar com prazo determinado | 16/07/2026 | 16/07/2028 | COMANDO DO EXERCITO (RJ) | Em todos os Poderes da Esfera do órgão sancionador | não |
| INFINITI EMPREENDIMENTOS LTDA | `23829339000109` | CNPJ | 2 (R$ 2.090) | Impedimento/proibição de contratar com prazo determinado | 05/12/2025 | 05/12/2028 | PREFEITURA DE BELO JARDIM - PE (PE) | Em todos os Poderes da Esfera do órgão sancionador | não |
| INFINITI EMPREENDIMENTOS LTDA | `23829339000109` | CNPJ | 2 (R$ 2.090) | Impedimento/proibição de contratar com prazo determinado | 07/07/2025 | 07/01/2027 | Câmara Municipal de Cianorte (PR) (PR) | Em todos os Poderes da Esfera do órgão sancionador | não |
| INFINITI EMPREENDIMENTOS LTDA | `23829339000109` | CNPJ | 2 (R$ 2.090) | Impedimento/proibição de contratar com prazo determinado | 12/06/2026 | 12/06/2028 | PREFEITURA MUNICIPAL DE CAMPO BELO-MG (MG) | Em todos os Poderes da Esfera do órgão sancionador | não |
| INFINITI EMPREENDIMENTOS LTDA | `23829339000109` | CNPJ | 2 (R$ 2.090) | Impedimento/proibição de contratar com prazo determinado | 13/10/2026 | 13/02/2029 | PREFEITURA MUNICIPAL DE DIVINÓPOLIS - MG (MG) | Em todos os Poderes da Esfera do órgão sancionador | não |
| INFINITI EMPREENDIMENTOS LTDA | `23829339000109` | CNPJ | 2 (R$ 2.090) | Impedimento/proibição de contratar com prazo determinado | 28/07/2026 | 28/10/2026 | UNIVERSIDADE FEDERAL DE ALAGOAS (AL) | Todas as Esferas em todos os Poderes | não |
| LICITA CERTA LTDA | `63045881000187` | CNPJ | 1 (R$ 11.580) | Impedimento/proibição de contratar com prazo determinado | 16/09/2026 | 16/12/2026 | INST.CHICO MENDES DE CONSER.DA BIODIVERSIDADE (DF) | Em todos os Poderes da Esfera do órgão sancionador | não |
| LICITA INFORMATICA LTDA | `56607352000164` | CNPJ | 1 (R$ 15.016) | Impedimento/proibição de contratar com prazo determinado | 15/09/2026 | 28/10/2026 | MIN.DA GEST.E DA INOVACAO EM SERVICOS PUBLICO (DF) | Em todos os Poderes da Esfera do órgão sancionador | **sim**: 30/09/2026 |
| MADIMBA EMPREENDIMENTOS LTDA | `47759958000124` | CNPJ | 1 (R$ 6.000) | Impedimento/proibição de contratar com prazo determinado | 10/06/2026 | 10/06/2027 | Prefeitura Municipal de Palhoça - SC (SC) | Em todos os Poderes da Esfera do órgão sancionador | **sim**: 07/10/2026 |
| MADIMBA EMPREENDIMENTOS LTDA | `47759958000124` | CNPJ | 1 (R$ 6.000) | Impedimento/proibição de contratar com prazo determinado | 11/02/2026 | 11/02/2029 | Prefeitura Municipal de Ituporanga (SC) (SC) | No órgão sancionador | **sim**: 07/10/2026 |
| MADIMBA EMPREENDIMENTOS LTDA | `47759958000124` | CNPJ | 1 (R$ 6.000) | Impedimento/proibição de contratar com prazo determinado | 17/07/2026 | 17/07/2028 | Prefeitura Municipal de São Bento do Sul (SC) (SC) | Em todos os Poderes da Esfera do órgão sancionador | **sim**: 07/10/2026 |
| NORTE TURISMO LTDA | `05570254000169` | CNPJ | 1 (R$ 308.912) | Suspensão | 30/04/2026 | 29/04/2028 | MINISTERIO PUBLICO DA UNIAO (DF) | No órgão sancionador | não |
| PORTUM DISTRIBUIDOR INDUSTRIAL LTDA | `48610545000146` | CNPJ | 1 (R$ 17.600) | Impedimento/proibição de contratar com prazo determinado | 24/06/2025 | 23/06/2028 | Prefeitura Municipal de Ireneópolis (SC) (SC) | Em todos os Poderes da Esfera do órgão sancionador | **sim**: 20/02/2026 |
| R S SOLUCOES COMERCIO E SERVICOS LTDA | `45852816000181` | CNPJ | 1 (R$ 26.750) | Impedimento/proibição de contratar com prazo determinado | 31/08/2026 | 31/08/2028 | PRESIDENCIA DA REPUBLICA (DF) | Em todos os Poderes da Esfera do órgão sancionador | não |
| SILVA DISTRIBUIDORA E FERRAGISTA LTDA | `45309056000160` | CNPJ | 1 (R$ 18.850) | Suspensão | 08/10/2026 | 08/10/2028 | EDF-SECRETARIA DE ADMINISTRAÇÃO PENITENCIÁRIA (DF) | No órgão sancionador | não |
| SUL AGUA EQUIPAMENTOS LTDA | `46344050000197` | CNPJ | 2 (R$ 90.917) | Impedimento/proibição de contratar com prazo determinado | 12/09/2025 | 11/09/2027 | CONSELHO REGION. DE ENGENHARIA E AGRONOMIA/PR (PR) | Em todos os Poderes da Esfera do órgão sancionador | não |
| SUL AGUA EQUIPAMENTOS LTDA | `46344050000197` | CNPJ | 2 (R$ 90.917) | Impedimento/proibição de contratar com prazo determinado | 19/02/2025 | 19/02/2028 | PREFEITURA DE PRUDENTÓPOLIS - PR (PR) | Em todos os Poderes da Esfera do órgão sancionador | **sim**: 02/06/2025 |
| SUL AGUA EQUIPAMENTOS LTDA | `46344050000197` | CNPJ | 2 (R$ 90.917) | Impedimento/proibição de contratar com prazo determinado | 19/05/2026 | 18/05/2027 | COMANDO DO EXERCITO (DF) | Em todos os Poderes da Esfera do órgão sancionador | não |
| SUL AGUA EQUIPAMENTOS LTDA | `46344050000197` | CNPJ | 2 (R$ 90.917) | Impedimento/proibição de contratar com prazo determinado | 19/06/2026 | 18/06/2027 | EES-POLÍCIA CIENTÍFICA E.DO ESPÍRITO SANTO (ES) | Em todos os Poderes da Esfera do órgão sancionador | não |
| SUL AGUA EQUIPAMENTOS LTDA | `46344050000197` | CNPJ | 2 (R$ 90.917) | Impedimento/proibição de contratar com prazo determinado | 20/10/2025 | 19/10/2027 | CONSELHO REGION. DE ENGENHARIA E AGRONOMIA/PR (PR) | Em todos os Poderes da Esfera do órgão sancionador | não |
| SUL AGUA EQUIPAMENTOS LTDA | `46344050000197` | CNPJ | 2 (R$ 90.917) | Impedimento/proibição de contratar com prazo determinado | 24/09/2026 | 24/09/2027 | Prefeitura Municipal de Sobral (CE) (CE) | No órgão sancionador | não |
| SUL AGUA EQUIPAMENTOS LTDA | `46344050000197` | CNPJ | 2 (R$ 90.917) | Impedimento/proibição de contratar com prazo determinado | 28/11/2024 | 28/11/2026 | SEMASA (SC) | Em todos os Poderes da Esfera do órgão sancionador | **sim**: 02/06/2025 |
| SUL AGUA EQUIPAMENTOS LTDA | `46344050000197` | CNPJ | 2 (R$ 90.917) | Impedimento/proibição de contratar com prazo determinado | 28/11/2024 | 28/11/2026 | SERVIÇO MUN. DE AGUA E SANEA BAS E INFRAE. (SC) | Em todos os Poderes da Esfera do órgão sancionador | **sim**: 02/06/2025 |
| SUL AGUA EQUIPAMENTOS LTDA | `46344050000197` | CNPJ | 2 (R$ 90.917) | Impedimento/proibição de contratar com prazo determinado | 31/07/2026 | 31/07/2027 | Tribunal de Contas do Estado do Rio de Janeiro - TCE-RJ (RJ) | Em todos os Poderes da Esfera do órgão sancionador | não |
| SUL AGUA EQUIPAMENTOS LTDA | `46344050000197` | CNPJ | 2 (R$ 90.917) | Impedimento/proibição de contratar com prazo determinado | 31/07/2026 | 31/07/2027 | TRIBUNAL DE CONTAS DO ESTADO DO R. DE JANEIRO (RJ) | Em todos os Poderes da Esfera do órgão sancionador | não |
| SUPER LICITE LICITACOES LTDA | `33275120000150` | CNPJ | 1 (R$ 11.038) | Impedimento/proibição de contratar com prazo determinado | 10/03/2026 | 10/10/2027 | PREFEITURA MUNICIPAL DE GUARULHOS - SP (SP) | Em todos os Poderes da Esfera do órgão sancionador | não |
| SUPER LICITE LICITACOES LTDA | `33275120000150` | CNPJ | 1 (R$ 11.038) | Impedimento/proibição de contratar com prazo determinado | 29/07/2026 | 29/03/2028 | MINISTERIO PUBLICO DA UNIAO (TO) | Em todos os Poderes da Esfera do órgão sancionador | não |
| SUPER LICITE LICITACOES LTDA | `33275120000150` | CNPJ | 1 (R$ 11.038) | Impedimento/proibição de contratar com prazo determinado | 31/07/2026 | 30/07/2027 | TRIBUNAL SUPERIOR DO TRABALHO TST (SC) | Em todos os Poderes da Esfera do órgão sancionador | não |
| VIXBOT SOLUCOES EM INFORMATICA LTDA | `21997155000203` | CNPJ | 1 (R$ 41.485) | Impedimento/proibição de contratar com prazo determinado | 11/07/2025 | 11/07/2028 | ASSEMBLÉIA LEGISLATIVA DA PARAÍBA (PB) | Em todos os Poderes da Esfera do órgão sancionador | não |

**CNEP** (arquivo de 20261022): 0 fornecedor(es), 0 registro(s) de sanção

## Completude: 15 órgãos e 441 contratos é tudo?

**Resposta curta: não. O PNCP de Belém está claramente incompleto**, tanto em órgãos quanto em valor. O que está lá foi
baixado inteiro (a API e a busca do site batem registro a registro); o que falta nunca foi publicado no PNCP.
Script: `scripts/completude.py` (`fetch` + `report`); saída bruta em `data/completude.md`.

### 1. Órgãos

Como a lista foi montada (23/10/2026):
- **Receita (CNPJ 2026-10):** todos os estabelecimentos com endereço em Belém/PA e natureza jurídica de ente municipal
  (órgão do Executivo, Legislativo, autarquia, fundação, fundo, Município, órgão autônomo) ou empresa pública/economia mista
  com "BELEM" no nome: **68 estabelecimentos**, 62 ativos.
- **Registro de órgãos do PNCP** (`/api/pncp/v1/orgaos`, ≈ 98,5 mil órgãos; o filtro por razão social é ignorado pela API
  e vem tudo): os 86 órgãos municipais com "BELEM" no nome, conferidos pela unidade em `codigoIbge=1501402`.
- **Contratações de 2026 por município** (`codigoMunicipioIbge=1501402`, 14 modalidades) e busca do site: 2 órgãos novos.
- O SICONFI não serve para isto: tem um único ente (`1501402`), sem os CNPJs da indireta.

Resultado: **59 CNPJs consultados um a um na API de contratos (2021–2026) e de atas (2024–2026); 15 com contrato, 44 sem
nenhum.** Entre os sem contrato estão a Câmara, o Fundo Municipal de Saúde, a SEINFRA (obras), a Superintendência de
Mobilidade (SEMOB), a ARBEL, a Fundação Cultural (FUMBEL), a Belém Digital (empresa municipal de TI aberta em 1983, provavelmente a antiga CINBESA), a FUNBOSQUE, a SEMEL, a SETUR e
todos os fundos. Cinco CNPJs ativos de secretarias novas (SECULT, SEMCAD, Ciência e Tecnologia e
dois fundos) nem estão no registro do PNCP.

**Unidades.** Cada CNPJ com contrato publica por uma única unidade. Sob o CNPJ do Município (`05055009000113`), só a
unidade `925387` (Prefeitura) tem contratos; as unidades da SEURB (`925905`), do Gabinete (`927398`), de Assuntos
Jurídicos (`926327`) e da Agência Distrital de Mosqueiro (`930684`) estão cadastradas e vazias. As secretarias não estão
"escondidas" sob o CNPJ da Prefeitura.

Universo: 68 estabelecimentos de natureza pública municipal com endereço em Belém/PA na base CNPJ (Receita, 2026-10), 62 deles no registro de órgãos do PNCP; 15 CNPJs com ao menos um contrato no PNCP.

| CNPJ | Entidade | Natureza | Situação Receita | No registro PNCP | Contratos PNCP (total) | No escopo 2024–26 | Unidades com contrato |
|---|---|---|---|---|---:|---:|---:|
| `05055033000152` | SECRETARIA MUNICIPAL DE EDUCACAO - SEMEC | Órgão do Executivo municipal | ativa | sim | 219 | 219 | 1 |
| `05055009000113` | MUNICIPIO DE BELEM | Município | ativa | sim | 56 | 56 | 1 |
| `49159407000155` | GUARDA MUNICIPAL DE BELEM | Órgão do Executivo municipal | ativa | sim | 40 | 40 | 1 |
| `59815458000141` | SECRETARIA MUNICIPAL DE SEGURANCA, ORDEM PUBLICA E MOBILIDADE DE BELEM - SEGBEL | Órgão do Executivo municipal | ativa | sim | 32 | 32 | 1 |
| `04789822000154` | SECRETARIA MUNICIPAL DE ZELADORIA E CONSERVACAO URBANA - SEZEL | Órgão do Executivo municipal | ativa | sim | 26 | 26 | 1 |
| `07917818000112` | SESMA-SECRETARIA MUNICIPAL DE SAUDE E MEIO AMBIENTE | Órgão do Executivo municipal | ativa | sim | 13 | 13 | 1 |
| `05065644000181` | FUNDACAO PAPA JOAO XXIII | Fundação pública municipal | ativa | sim | 12 | 12 | 1 |
| `05055025000106` | BELEM SECRETARIA MUNICIPAL DE FINANCAS | Órgão do Executivo municipal | ativa | sim | 10 | 10 | 1 |
| `59870569000150` | SECRETARIA MUNICIPAL DA MULHER | Órgão do Executivo municipal | ativa | sim | 9 | 9 | 1 |
| `05055009000628` | MUNICIPIO DE BELEM | Município | ativa | sim | 8 | 8 | 1 |
| `29331615000182` | BELEMPREV | Autarquia municipal | ativa | sim | 7 | 7 | 1 |
| `09551008000110` | CONTROLADORIA-GERAL DO MUNICIPIO | Órgão do Executivo municipal | ativa | sim | 4 | 4 | 1 |
| `59693965000150` | SECRETARIA MUNICIPAL DE COMUNICACAO - SECOM | Órgão do Executivo municipal | ativa | sim | 3 | 3 | 1 |
| `14700173000127` | SECRETARIA MUNIC.DE COORD.GERAL DO PLANEJAM.E GESTAO | Órgão do Executivo municipal | ativa | sim | 1 | 1 | 1 |
| `10245579000106` | SECRETARIA MUNICIPAL DE DESENVOLVIMENTO ECONOMICO -SEDCON | Órgão do Executivo municipal | ativa | sim | 1 | 1 | 1 |
| `05205194000185` | ADMINISTRACAO REGIONAL DO OUTEIRO | Órgão do Executivo municipal | ativa | sim | 0 | 0 | 0 |
| `83752790000199` | AGENCIA DISTRITAL DO MOSQUEIRO | Órgão do Executivo municipal | ativa | sim | 0 | 0 | 0 |
| `19670696000191` | AGENCIA REGULADORA MUNICIPAL DE BELEM - ARBEL | Autarquia municipal | ativa | sim | 0 | 0 | 0 |
| `07303818000122` | BELEM PREFEITURA GABINETE DO VICE PREFEITO | Órgão do Executivo municipal | ativa | sim | 0 | 0 | 0 |
| `05416029000172` | CAMARA MUNICIPAL DE BELEM | Legislativo municipal | ativa | sim | 0 | 0 | 0 |
| `00986621000196` | CENTRO REF ED AMBIENT ESCOLA BOSQ. PROF EIDORFE MOREIRA | Fundação pública municipal | ativa | sim | 0 | 0 | 0 |
| `04977583000166` | CIA DE DESEMVOLV E ADM DA AREA METROPOLITANA DE BELEM | Sociedade de economia mista | ativa | não | 0 | 0 | 0 |
| `15149265000123` | COMISSAO MUNICIPAL DE DEFESA CIVIL DE BELEM - COMDEC | Órgão do Executivo municipal | ativa | sim | 0 | 0 | 0 |
| `04850095000193` | COMPANHIA DE TRANSFORMACAO DIGITAL DO MUNICIPIO DE BELEM - BELEM DIGITAL | Sociedade de economia mista | ativa | sim | 0 | 0 | 0 |
| `14068357000116` | COMUS COORDENADORIA DE COMUNICACAO SOCIAL | Órgão do Executivo municipal | ativa | sim | 0 | 0 | 0 |
| `34847335000161` | FUNDACAO CULTURAL DO MUNICIPIO DE BELEM | Fundação pública municipal | ativa | sim | 0 | 0 | 0 |
| `15742539000193` | FUNDACAO MUNICIPAL DE ASSISTENCIA AO ESTUDANTE | Fundação pública municipal | ativa | sim | 0 | 0 | 0 |
| `67056178000125` | FUNDO ESPECIAL DA PROCURADORIA-GERAL DO MUNICIPIO  FEPGM | Fundo da direta municipal | ativa | não | 0 | 0 | 0 |
| `14684151000110` | FUNDO MUNICIPAL DE ASSISTENCIA SOCIAL DO MUNICPIO DE BELEM | Fundo da direta municipal | ativa | sim | 0 | 0 | 0 |
| `11305777000180` | FUNDO MUNICIPAL DE SAUDE | Fundo da direta municipal | ativa | sim | 0 | 0 | 0 |
| `67273416000154` | FUNDO MUNICIPAL DE SEGURANCA, ORDEM PUBLICA, MOBILIDADE, TRNSITO, DEFESA CIVIL E CULTURA DA PAZ | Fundo da direta municipal | ativa | não | 0 | 0 | 0 |
| `21700218000129` | FUNDO MUNICIPAL DE SOLIDARIEDADE PARA GERACAO DE EMPREGO E RENDA VER-O-SOL | Órgão do Executivo municipal | ativa | sim | 0 | 0 | 0 |
| `18869413000172` | FUNDO MUNICIPAL DOS DIREITOS DA CRIANCA E DO ADOLESCENTE | Fundo da direta municipal | ativa | sim | 0 | 0 | 0 |
| `30513019000100` | GABINETE DO PREFEITO DO MUNICIPIO DE BELEM | Órgão do Executivo municipal | ativa | sim | 0 | 0 | 0 |
| `29331512000112` | INSTITUTO DE ASSISTENCIA A SAUDE DOS SERVIDORES PUBLICOS DO MUNICIPIO DE BELEM | Autarquia municipal | ativa | sim | 0 | 0 | 0 |
| `05055009000385` | MUNICIPIO DE BELEM | Município | ativa | sim | 0 | 0 | 0 |
| `05055009001004` | MUNICIPIO DE BELEM | Município | ativa | sim | 0 | 0 | 0 |
| `05055009001195` | MUNICIPIO DE BELEM | Município | ativa | sim | 0 | 0 | 0 |
| `05055009000466` | MUNICIPIO DE BELEM | Município | ativa | sim | 0 | 0 | 0 |
| `05055009000547` | MUNICIPIO DE BELEM | Município | ativa | sim | 0 | 0 | 0 |
| `05055009000970` | MUNICIPIO DE BELEM | Município | ativa | sim | 0 | 0 | 0 |
| `05055009000202` | MUNICIPIO DE BELEM | Município | ativa | sim | 0 | 0 | 0 |
| `05055009000709` | MUNICIPIO DE BELEM | Município | ativa | sim | 0 | 0 | 0 |
| `05055009000890` | MUNICIPIO DE BELEM | Município | ativa | sim | 0 | 0 | 0 |
| `05055009001276` | MUNICIPIO DE BELEM | Município | ativa | sim | 0 | 0 | 0 |
| `11536671000198` | OUVIDORIA GERAL DO MUNICIPIO DE BELEM | Órgão do Executivo municipal | ativa | sim | 0 | 0 | 0 |
| `03223035000188` | P M B - AGENCIA DISTRITAL DE ICOARACI | Órgão do Executivo municipal | ativa | sim | 0 | 0 | 0 |
| `14098990000157` | PROCURADORIA GERAL DO MUNICIPIO - PGM | Órgão do Executivo municipal | ativa | sim | 0 | 0 | 0 |
| `59819427000169` | SECRETARIA MUNICIPAL DE AGRICULTURA E PESCA - SEAPE | Órgão do Executivo municipal | ativa | sim | 0 | 0 | 0 |
| `53506046000143` | SECRETARIA MUNICIPAL DE CIDADANIA, ASSISTENCIAL SOCIAL E DIREITOS HUMANOS - SEMCAD | Órgão do Executivo municipal | ativa | não | 0 | 0 | 0 |
| `64915369000107` | SECRETARIA MUNICIPAL DE CIENCIA E TECNOLOGIA | Órgão do Executivo municipal | ativa | não | 0 | 0 | 0 |
| `64574450000170` | SECRETARIA MUNICIPAL DE CULTURA - SECULT | Órgão do Executivo municipal | ativa | não | 0 | 0 | 0 |
| `09453989000163` | SECRETARIA MUNICIPAL DE ESPORTE E LAZER - SEMEL | Órgão do Executivo municipal | ativa | sim | 0 | 0 | 0 |
| `05055017000160` | SECRETARIA MUNICIPAL DE GOVERNO | Órgão do Executivo municipal | ativa | sim | 0 | 0 | 0 |
| `02346546000124` | SECRETARIA MUNICIPAL DE HABITACAO / PREFEITURA MUNICIPAL DE BELEM | Órgão do Executivo municipal | ativa | sim | 0 | 0 | 0 |
| `59631344000141` | SECRETARIA MUNICIPAL DE INCLUSAO E ACESSIBILIDADE - SEMIAC | Órgão do Executivo municipal | ativa | sim | 0 | 0 | 0 |
| `05544392000173` | SECRETARIA MUNICIPAL DE MEIO AMBIENTE | Órgão do Executivo municipal | ativa | sim | 0 | 0 | 0 |
| `05055041000107` | SECRETARIA MUNICIPAL DE OBRAS E INFRAESTRUTURA - SEINFRA | Órgão do Executivo municipal | ativa | sim | 0 | 0 | 0 |
| `54305300000108` | SECRETARIA MUNICIPAL DE PROTECAO E DEFESA DOS ANIMAIS | Órgão do Executivo municipal | ativa | sim | 0 | 0 | 0 |
| `59927733000119` | SECRETARIA MUNICIPAL DE TRABALHO E EMPREGO - SEMTE | Órgão do Executivo municipal | ativa | sim | 0 | 0 | 0 |
| `06066036000154` | SECRETARIA MUNICIPAL DE TURISMO - SETUR | Órgão do Executivo municipal | ativa | sim | 0 | 0 | 0 |
| `63803100000176` | SUPERINTENDENCIA EXECUTIVA DE MOBILIDADE URBANA DE BELEM | Autarquia municipal | ativa | sim | 0 | 0 | 0 |

6 estabelecimentos baixados/inaptos/nulos omitidos da tabela.

Unidades (códigos de unidade gestora) com contrato no PNCP:

| Órgão (CNPJ) | Unidade | Contratos | No escopo |
|---|---|---:|---:|
| `04789822000154` | 930676 CPA-SECRETARIA MUNICIPAL DE SANEAMENTO | 26 | 26 |
| `05055009000113` | 925387 PREFEITURA MUNICIPAL DE BELÉM | 56 | 56 |
| `05055009000628` | 930666 PMPA - GUARDA MUNICIPAL DE BELÉM | 8 | 8 |
| `05055025000106` | 929350 CPA-SECRETARIA MUNICIPAL DE FINANÇAS DE BELÉM | 10 | 10 |
| `05055033000152` | 926381 SECRETARIA MUNICIPAL DE EDUCACAO DE BELEM-PA | 219 | 219 |
| `05065644000181` | 930668 CPA-FUNDAÇAO PAPA JOÃO XXIII | 12 | 12 |
| `07917818000112` | 926294 CPA-SECRETARIA MUNICIPAL SAUDE MEIO AMBIENTE | 13 | 13 |
| `09551008000110` | 928343 CPA-SECRETARIA MUN.CONT.INTEG.E TRANSPARÊNCIA | 4 | 4 |
| `10245579000106` | 926322 PMPA - SECRETARIA MUNICIPAL DE ECONOMIA | 1 | 1 |
| `14700173000127` | 927970 CPA-SECRETARIA MU DE CO.GER DO PLAN.E GESTÃO | 1 | 1 |
| `29331615000182` | 930730 PMPA-INSTITUTO DE PREV. SERVIDORES PÚBLICOS | 7 | 7 |
| `49159407000155` | 930666 PMPA - GUARDA MUNICIPAL DE BELÉM | 40 | 40 |
| `59693965000150` | 933075 CPA-SECRETARIA MUNICIPAL DE COMUNICACAO | 3 | 3 |
| `59815458000141` | 932950 CPA-SECRETARIA MUN. SEG. O. P. E MOBILIDADE | 32 | 32 |
| `59870569000150` | 932857 CPA-SECRETARIA MUNICIPAL DA MULHER | 9 | 9 |

### 2. Valor

Comparação com a despesa do SICONFI (RREO Anexo 01, Prefeitura + Câmara, sem intraorçamentárias) **sem pessoal e encargos
e sem juros e amortização da dívida** (sobram outras despesas correntes, investimentos e inversões financeiras). Do lado
do PNCP, contratos e aditivos vigentes no período, com o valor global distribuído pelos dias de vigência.

| Ano | Despesa SICONFI sem pessoal e dívida, empenhada | idem, liquidada | Período | Contratos PNCP vigentes (pro rata no período) | Cobertura (pro rata ÷ empenhado) | Soma bruta do valor global dos vigentes |
|---|---:|---:|---|---:|---:|---:|
| 2024 | R$ 2.967.093.129 | R$ 2.915.012.097 | jan–dez | R$ 18.913.595 | 0.6% | R$ 32.499.253 |
|  | excluído: Pessoal e encargos R$ 2.360.844.556; Juros da dívida R$ 126.787.554; Amortização da dívida R$ 122.310.720 |  |  |  |  |  |
| 2025 | R$ 2.729.757.726 | R$ 2.603.592.807 | jan–dez | R$ 231.600.464 | 8.5% | R$ 656.894.000 |
|  | excluído: Pessoal e encargos R$ 2.372.658.506; Juros da dívida R$ 164.434.404; Amortização da dívida R$ 157.824.201 |  |  |  |  |  |
| 2026 | R$ 2.044.132.608 | R$ 1.802.535.740 | jan–ago | R$ 486.532.624 | 23.8% | R$ 1.073.204.264 |
|  | excluído: Pessoal e encargos R$ 1.550.302.443; Juros da dívida R$ 94.238.159; Amortização da dívida R$ 111.015.550 |  |  |  |  |  |

Leitura:
- **2024: 0,6%; 2025: 8,5%; jan–ago/2026: 23,8%.** O PNCP só passa a ter volume em 2025 (226 contratos assinados), e a
  maior parte é da SEMEC.
- O número de 2026 é um **teto**: o valor global de contrato de registro de preço ou "sob demanda" não é executado
  integralmente. A cobertura real, medida em pagamento, deve ser menor.
- **100% não é a meta.** Parte das "outras despesas correntes" nunca tem contrato no PNCP: repasses SUS a prestadores,
  subvenções e transferências a entidades, auxílios, contas de consumo, diárias, PASEP. Mesmo assim, uma cobertura de 10% a
  25% e quase zero em Saúde, Transporte, Urbanismo e Administração indica que **a maior parte do gasto contratado não está no
  PNCP**.

Por função, jan–ago/2026. Atenção: o RREO Anexo 02 **inclui pessoal**, então a razão é um piso, não uma cobertura; o PNCP foi agrupado pelo órgão contratante (SESMA→Saúde, SEMEC→Educação, Saneamento→Saneamento, Guarda/SEGBEL→Segurança Pública), o que é aproximado.

| Função | Empenhado SICONFI jan–ago/2026 (com pessoal) | Contratos PNCP pro rata jan–ago/2026 | Razão |
|---|---:|---:|---:|
| Saúde | R$ 964.907.010 | R$ 863.562 | 0.1% |
| Educação | R$ 812.270.340 | R$ 388.968.706 | 47.9% |
| Saneamento | R$ 598.136.035 | R$ 66.520.196 | 11.1% |
| Encargos Especiais | R$ 525.716.056 | R$ 0 | 0.0% |
| Assistência Social | R$ 145.442.443 | R$ 2.551.297 | 1.8% |
| Transporte | R$ 131.268.632 | R$ 0 | 0.0% |
| Legislativa | R$ 120.039.584 | R$ 0 | 0.0% |
| Administração | R$ 106.233.473 | R$ 0 | 0.0% |
| Segurança Pública | R$ 103.758.368 | R$ 22.089.497 | 21.3% |
| Urbanismo | R$ 100.258.059 | R$ 0 | 0.0% |
| Habitação | R$ 28.662.864 | R$ 0 | 0.0% |
| Comércio e Serviços | R$ 26.908.112 | R$ 0 | 0.0% |
| Ciência e Tecnologia | R$ 24.098.371 | R$ 0 | 0.0% |
| Comunicações | R$ 23.946.175 | R$ 0 | 0.0% |
| (contratos de outros órgãos) | — | R$ 5.482.505 | — |

### 3. API × site

A busca do site (`/api/search`, `municipios=1501402`, `esferas=M`, todos os status) declara 441 contratos municipais de
Belém; baixamos os 441 (com a ordenação invertida para contornar a página que o servidor derruba) e a API de consulta
(`/v1/contratos` por CNPJ) devolve exatamente os mesmos 441, órgão por órgão, sem sobra de nenhum lado. **Não há buraco de
paginação nem de filtro.** As duas leem a mesma base, então esta checagem não detecta o que nunca foi publicado.

Busca do site (`/api/search`, municípios=1501402, esfera M, todos os status): total declarado 441, 441 contratos distintos baixados.

| Órgão | API consulta | Busca do site | Só na API | Só no site |
|---|---:|---:|---:|---:|
| `05055033000152` SEMEC | 219 | 219 | 0 | 0 |
| `05055009000113` Município de Belém | 56 | 56 | 0 | 0 |
| `49159407000155` Guarda Municipal | 40 | 40 | 0 | 0 |
| `59815458000141` SEGBEL | 32 | 32 | 0 | 0 |
| `04789822000154` Saneamento | 26 | 26 | 0 | 0 |
| `07917818000112` SESMA | 13 | 13 | 0 | 0 |
| `05065644000181` Fundação Papa João XXIII | 12 | 12 | 0 | 0 |
| `05055025000106` SEFIN | 10 | 10 | 0 | 0 |
| `59870569000150` Secretaria da Mulher | 9 | 9 | 0 | 0 |
| `05055009000628` Município de Belém (filial) | 8 | 8 | 0 | 0 |
| `29331615000182` Instituto de Previdência | 7 | 7 | 0 | 0 |
| `09551008000110` SECONT | 4 | 4 | 0 | 0 |
| `59693965000150` SECOM | 3 | 3 | 0 | 0 |
| `10245579000106` Economia | 1 | 1 | 0 | 0 |
| `14700173000127` Planejamento e Gestão | 1 | 1 | 0 | 0 |

### 4. Ordem de grandeza e como fechar a lacuna

- **Veredito: claramente incompleto.** 15 de 59 entidades publicam contratos; em valor, o PNCP cobre de menos de 1% a 24% da despesa
  não salarial, e praticamente nada em Saúde, a maior função do município.
- **Fontes que fecham a lacuna (todas exigem IP brasileiro, ver `fontes/fontes.md`):**
  1. **Portal da Transparência de Belém (GIIG):** empenhos, liquidações e pagamentos por credor, de todas as entidades. É a
     fonte que dá o total pago por fornecedor e permite medir quanto do pago tem contrato.
  2. **Mural de Licitações do TCM-PA:** por lei estadual, todos os contratos, convênios e aditivos dos municípios do Pará.
  3. **Diário Oficial do Município:** extratos de contrato, aditivos e dispensas.
- Funciona daqui e pode entrar já: a exportação de contratos do site da Câmara (`cmb.pa.gov.br/transparencia/contratos/exportar`).


## Próximo passo sugerido

VPS ou coletor com IP brasileiro para o GIIG da Prefeitura (pagamentos por credor de 2026) e o Mural do TCM-PA; com isso, medir quanto do pago em 2026 tem contrato identificável e refazer o ranking por valor **pago**. Enquanto isso, daqui: carregar os contratos da Câmara pelo site dela e rodar os indicadores do handoff §6.1 que só pedem PNCP × CNPJ (empresa recém-aberta, capacidade, CNAE × objeto, sócios em comum).

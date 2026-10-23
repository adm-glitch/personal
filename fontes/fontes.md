# Inventário testado das fontes (Fase 0)

> Testado em **23/10/2026** (madrugada, UTC) a partir de uma VPS **Hetzner nos EUA** (Oregon; IPv4 `5.78.135.54`,
> IPv6 `2a01:4ff:1f0:1d0b::1`). Substitui a seção 4 de `docs/handoff-2026-10-23.md`.
> User-Agent `observatorio-belem/0.1 (pesquisa civica; contato via github adm-glitch)`, ≥ 1,1 s entre requisições por host,
> só amostras. O bruto de cada teste está em `raw/<fonte>/2026-10-23/` com `meta.json` (URL, hora UTC, status,
> cabeçalhos, erro). `raw/` não vai para o git. Scripts: `scripts/fase0_probe.py` (sonda genérica) e
> `scripts/fase0_giig_postback.py` (prova de raspagem do GIIG).
>
> Bloqueio geográfico confirmado de fora com o check-host.net (nó em São Paulo × nós nos EUA, Canadá, Europa e Ásia):
> evidência em `raw/geoblock-check/2026-10-23/meta.json`.

Legenda: ✅ funciona · ⚠️ parcial · ⛔ bloqueado no exterior · ❌ não existe / fora do ar

Identificadores confirmados:
- **Município de Belém (Prefeitura): CNPJ `05.055.009/0001-13`** ✅ — razão social "MUNICIPIO DE BELEM", natureza
  jurídica Município, CNAE 8411-6/00, Palácio Antônio Lemos (BrasilAPI e minhareceita.org); o SICONFI usa o mesmo CNPJ
  para o ente 1501402; no PNCP é o órgão id 93010, unidade principal `925387`.
- **IBGE 1501402**, população SICONFI 2026: 1.397.315.
- Infra da Prefeitura: os domínios `*.belem.pa.gov.br` (transparencia, diario, belemprev, www, sistemas) resolvem para
  `187.73.105.0/26`, **CINBESA** (Companhia de Informática de Belém, AS53048). É essa rede que bloqueia o exterior.

---

## 1. Contratos e licitações

| Fonte | Testado em | Resultado | Acesso real (endpoint, formato, auth, paginação) | Cobertura 2026 | Observações |
|---|---|---|---|---|---|
| **PNCP: API de consulta** | 23/10/2026 | ✅ | Swagger: `https://pncp.gov.br/api/consulta/v3/api-docs`. **Contratos:** `GET /api/consulta/v1/contratos?dataInicial=AAAAMMDD&dataFinal=AAAAMMDD&cnpjOrgao=<cnpj>&pagina=N&tamanhoPagina≤50`: **não aceita município**, só `cnpjOrgao`/`codigoUnidadeAdministrativa`. **Compras:** `GET /api/consulta/v1/contratacoes/publicacao?...&codigoModalidadeContratacao=<obrigatório>&codigoMunicipioIbge=1501402`. JSON, sem chave, paginação `totalRegistros/totalPaginas/paginasRestantes`. Órgão e unidades: `GET /api/pncp/v1/orgaos/{cnpj}` e `/unidades`. | Sim. PMB (`05055009000113`), 2026: **24 contratos**; SESMA (`07917818000112`): **13**. | Lento e instável: 0,7 s a 69 s por chamada; a janela de 10 meses estourou 30 s na 1ª tentativa e respondeu em 0,7 s na 2ª. Sem resultado = **HTTP 204**. `codigoMunicipioIbge=1501402` devolve **todas as esferas** com unidade em Belém (Exército, TJPA, SESPA, UFPA…): filtrar `orgaoEntidade.esferaId == "M"`. Setembro/2026: 237 pregões e 425 dispensas em Belém, quase tudo estadual/federal. A lista de unidades do CNPJ da PMB traz lixo de cadastro (uma "Câmara de Marmelópolis"). |
| **PNCP: API de busca** (a do site) | 23/10/2026 | ⚠️ | `GET https://pncp.gov.br/api/search/?tipos_documento=contrato&municipios=1501402&esferas=M&status=todos&ordenacao=-data&pagina=N&tam_pagina=100`. JSON com `total` e `items` (≈ 100 campos: órgão, unidade, fornecedor_ni/nome, modalidade, amparo legal, vigência, valor, `link_sistema_origem`). Sem chave. | Sim. **441 contratos municipais de Belém no total**, de 2022 a 2026; 341 baixados; **147 com ano 2026; 288 vigentes em 2026** (132 deles assinados antes de 2026). Atraso de publicação dos contratos de 2026: mediana de **6 dias**, p90 de 59 dias, máximo de 200 dias. | **É o melhor atalho para descobrir os CNPJs municipais** (seção 9.2, item 10). Instável: o servidor derruba a conexão (TCP reset) em algumas combinações de parâmetros (a página 4 sempre, `tipos_documento=edital` sem `q`, às vezes `q=belem` em minúsculas). Não é bloqueio de IP: outras consultas respondem 200 no mesmo minuto. Não é API documentada; pode mudar. |
| **Mural de Licitações do TCM-PA** | 23/10/2026 | ⛔ | `https://www.tcmpa.tc.br/portal-do-gestor/mural-de-licitacoes/` | Não verificado | **Cloudflare "Sorry, you have been blocked" (HTTP 403)** em IPv4 e IPv6 a partir da VPS. check-host: **200 OK do Brasil, 403 dos EUA**. É regra de WAF por país/ASN; não contornar. API e exportação continuam desconhecidas. |
| **Portal da Transparência de Belém (GIIG, Prefeitura)** | 23/10/2026 | ⛔ | `https://transparencia.belem.pa.gov.br/giig/portais/portaldatransparencia/...` | **Não verificável daqui** | **Timeout de TCP nas portas 80 e 443** (a conexão nunca abre). check-host: TCP abre em 2,0 s de São Paulo e dá timeout em 7 países; HTTP 302 do Brasil e timeout dos EUA. **O Wayback Machine não ajuda:** uma única captura desde 2025 (15/05/2025, página de patrimônio). Ver o GIIG da Câmara abaixo: é o mesmo software. |
| **GIIG da Câmara** (mesmo sistema Lexsom, outro servidor) | 23/10/2026 | ✅ | `http://187.122.249.37/GIIG/Portais/PortalDaTransparencia/Templates/wfrmPaginaVisoes.aspx?IdVisao=2` (link "Despesas" do site da Câmara; IP da Claro, fora da CINBESA). ASP.NET WebForms: GET → `__VIEWSTATE`/`__EVENTVALIDATION` → POST com datas `dd/mm/aaaa` e `btnbuscar`. HTML, sem login, sem captcha. | **Sim: "Última Data de Movimentação dos Dados: 19/10/2026 11:00:09"**. Um postback (09/2026) devolveu os empenhos com as colunas Empenho, Dt. Empenho, Credor, Despesa, Projeto/Atividade, Fonte, Empenhado, Anulado, Liquidado, Consignado, Pago e Saldo, além dos totais (empenhado R$ 10,97 mi; pago R$ 7,68 mi). | Só a Câmara (entidade única no combo). Resultado paginado por postback; detalhes em `wfrmExecutaChamada.aspx?IdEmpenho=` e anexos em `wfrmDownloadDocLiq.aspx?IdEmpenho=`. **Prova a técnica de raspagem do GIIG sem Playwright** (`scripts/fase0_giig_postback.py`). Exercícios no combo desde 2000. |
| **Diário Oficial do Município** | 23/10/2026 | ⛔ | `https://diario.belem.pa.gov.br/` e `http://sistemas.belem.pa.gov.br/diario/painel` | Não verificado | Timeout de TCP (rede CINBESA). check-host: **301 do Brasil**. |
| **Querido Diário** | 23/10/2026 | ⚠️ | **A API mudou de domínio:** `https://api.queridodiario.org.br` (o antigo `api.queridodiario.ok.org.br` falha no handshake TLS da Cloudflare). `GET /cities?city_name=Belém`, `GET /gazettes?territory_ids=1501402&published_since=&size=&sort_by=`. JSON, sem chave. PDF e TXT em `data.queridodiario.ok.org.br` (funciona). | **❌ Sem 2026.** Belém coberta de **01/02/2005 a 13/05/2025** (4.744 edições); fonte cadastrada `sistemas.belem.pa.gov.br/diario/painel`. | A coleta parou em maio/2025, provavelmente porque o raspador (que roda fora do Brasil?) perdeu acesso ou porque o diário mudou para `diario.belem.pa.gov.br`. **Contribuir com o raspador** continua sendo boa ideia, mas o raspador precisaria rodar de um IP brasileiro. O TXT já vem extraído (amostra: edição 15188, 136 KB). |
| **IOEPA: DOE do Pará** | 23/10/2026 | ✅ | `https://ioepa.com.br/pages/AAAA/AAAA.MM.DD.DOE.pdf` (Cloudflare, sem bloqueio) | Sim: a edição de 22/10/2026 já estava no ar (Last-Modified 22/10 11:06 UTC) | PDF de cerca de 20 MB por edição; amostra guardada com os primeiros 300 KB. Interessa para autarquias e atos estaduais; pouco para o município. |
| **Diário dos Municípios do Pará (FAMEP/SIGPub)** | 23/10/2026 | ✅ (site) | `https://www.diariomunicipal.com.br/famep/` | Não verificado se Belém publica | O endereço em Belém que aparece na página é o da própria FAMEP. Baixa prioridade. |
| **Câmara Municipal: site e dados abertos** | 23/10/2026 | ✅ | O caminho do handoff (`/portal-da-transparencia/dados-abertos/`) dá **404**. Os certos: `https://cmb.pa.gov.br/transparencia/contratos/exportar?formato=json\|csv\|xml` (sem chave) e `https://cmb.pa.gov.br/api/v1/dados-abertos/{vereadores,sessoes,proposicoes,legislacao,agenda,noticias,receitas,receitas-por-fonte,pagamentos-cronologicos}` (JSON com `meta.total/page/per_page`). | Sim: os contratos exportados (33) incluem **9 de 2026**. | `receitas` e `pagamentos-cronologicos` respondem **404 "Recurso indisponivel"**. Os contratos trazem CNPJ, valor, vigência, fiscal e URL. As despesas estão no GIIG da Câmara (acima). |
| **BelémPrev** | 23/10/2026 | ⛔ | `https://belemprev.belem.pa.gov.br/transparencia/` | Não verificado | Timeout (rede CINBESA). check-host: **200 OK do Brasil** em 6 s. No PNCP aparece o "Instituto de Previdência dos Servidores Públicos do Município de Belém" (`29331615000182`, 7 contratos). |

## 2. Orçamento e execução

| Fonte | Testado em | Resultado | Acesso real | Cobertura 2026 | Observações |
|---|---|---|---|---|---|
| **SICONFI (API Tesouro)** | 23/10/2026 | ✅ | `https://apidatalake.tesouro.gov.br/ords/siconfi/tt/`: `entes`, `extrato_entregas?id_ente=1501402&an_referencia=2026`, `rreo?an_exercicio=2026&nr_periodo=4&co_tipo_demonstrativo=RREO&no_anexo=RREO-Anexo%2002&co_esfera=M&id_ente=1501402`. JSON (ORDS, `hasMore`), sem chave, rápido (1–3 s). | **Sim.** RREO até o **4º bimestre/2026** (homologado em 30/09), RGF do 2º quadrimestre (30/09), MSC agregada até **agosto/2026** (entregue em 24/09). **Atraso de cerca de 1 mês.** | Anexo 02 (função/subfunção), liquidado até o 4º bimestre: Saúde R$ 956 mi, Educação R$ 717 mi, Saneamento R$ 566 mi, Assistência R$ 133 mi, Urbanismo R$ 86 mi. É o **único dado oficial de execução de 2026 do Executivo que acessamos daqui**. Sem fornecedor. Prefeitura e Câmara entregam separados. |
| **Portal da Transparência federal: API** | 23/10/2026 | ⚠️ | `https://api.portaldatransparencia.gov.br/api-de-dados/...` | — | **401 sem chave** ("Chave de API não informada"). A chave sai em `portaldatransparencia.gov.br/api-de-dados/cadastrar-email` (gov.br). |
| **Portal da Transparência federal: páginas** | 23/10/2026 | ⛔ (bot) | `/localidades/1501402-belem`, `/sancoes/ceis` | — | **HTTP 405 com "Human Verification" (desafio do AWS WAF)**. Não contornar. A página `/download-de-dados/ceis` abre normalmente (200). |

## 3. Empresas e pessoas

| Fonte | Testado em | Resultado | Acesso real | Cobertura 2026 | Observações |
|---|---|---|---|---|---|
| **CNPJ: dados abertos da Receita** | 23/10/2026 | ✅ | **Mudou de novo.** `dadosabertos.rfb.gov.br/CNPJ/` dá timeout; `arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/` dá 404. O certo é o Nextcloud "SERPRO+": `https://arquivos.receitafederal.gov.br/` redireciona para o share público `index.php/s/gn672Ad4CF8N6TK`. Listagem por WebDAV: `PROPFIND https://arquivos.receitafederal.gov.br/public.php/webdav/Dados/Cadastros/CNPJ/<AAAA-MM>/` (usuário = token do share, senha vazia; `Depth: 1`). | **Sim: pasta `2026-10` publicada em 13/10/2026**, com pastas mensais desde 2023-05. | Layout de sempre: `Empresas0-9.zip` (~1,4 GB), `Estabelecimentos0-9.zip` (~5,4 GB), `Socios0-9.zip` (~0,7 GB), `Simples.zip` (311 MB) e as tabelas de domínio (`Cnaes`, `Motivos`, `Municipios`, `Naturezas`, `Paises`, `Qualificacoes`). CSV `;` entre aspas, latin-1, sem cabeçalho. Total do mês: **≈ 7,8 GB zipado**. Também há um `cnpj.tar.gz` de 64 GB (o histórico inteiro). Amostra: `Naturezas.zip`. Há ainda as pastas `CNO` (obras) e `CAFIR` ao lado, úteis para as obras. Para consulta pontual, BrasilAPI e minhareceita.org respondem (✅). |
| **CEIS / CNEP** | 23/10/2026 | ✅ (download) / ⚠️ (API) | **Download sem chave:** `https://portaldatransparencia.gov.br/download-de-dados/ceis/AAAAMMDD` redireciona (302) para `https://dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida/ceis/AAAAMMDD_CEIS.zip`; o mesmo vale para `cnep`. ZIP com CSV `;` em latin-1. A API pede chave. | **Diário** (arquivo de 22/10/2026). | CEIS: 3,4 MB, **23.838 linhas**, 24 colunas (CPF/CNPJ do sancionado, categoria, datas, órgão sancionador, UF, esfera, fundamentação). **Dispensa a chave para o cruzamento.** |
| **TSE: dados abertos** | 23/10/2026 | ✅ | CKAN: `https://dadosabertos.tse.jus.br/api/3/action/package_search` / `package_show?id=prestacao-de-contas-eleitorais-2024`. Arquivos em `cdn.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2024.zip`. | n/a (eleições de 2020 e 2024) | O arquivo de 2024 dos candidatos tem **1,35 GB**, nacional; não há corte por UF nessa URL (o `_PA.zip` dá 404). Também há `CNPJ_campanha_2024.zip` e `fefc_fp_2024.zip`. |
| **Folha da Prefeitura** | 23/10/2026 | ⛔ | Estaria no portal da Prefeitura (rede CINBESA) | Não verificado | A Câmara publica folha em `cmb.pa.gov.br/transparencia/folha-pagamento`. |
| **Base dos Dados** | — | não testado | BigQuery | — | Desnecessária por ora: o CNPJ bruto baixa direto e o CEIS também. |

## 4. Território

| Fonte | Testado em | Resultado | Acesso real | Cobertura | Observações |
|---|---|---|---|---|---|
| **IBGE: malha de bairros do Censo 2022** | 23/10/2026 | ✅ | `https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_de_setores_censitarios__divisoes_intramunicipais/censo_2022/bairros/shp/UF/PA_bairros_CD2022.zip` (238 KB; também em GPKG e para o Brasil inteiro) | Censo 2022 | **71 bairros de Belém**, com código (`CD_BAIRRO`) e distrito: Mosqueiro 19, Belém 10, Entroncamento 10, Icoaraci 9, Bengui 8, Sacramenta 7, Guamá 4 e Outeiro 4. **Bate com os 71 bairros e os 8 distritos do handoff.** Há também setores censitários em `geoftp`. |
| **IBGE: API de localidades e de malhas** (`servicodados.ibge.gov.br`) | 23/10/2026 | ⛔ | `/api/v1/localidades/municipios/1501402/distritos`, `/api/v3/malhas/municipios/1501402` | — | **Timeout de TCP da VPS**; check-host: 200 do Brasil, timeout dos EUA. O `geoftp` do IBGE funciona. |
| **Malha da Prefeitura/CODEM** | — | não testado | — | — | Os sites da Prefeitura estão inacessíveis daqui. |

---

## Precisa da VPS no Brasil

Sem IP brasileiro não dá para avançar nestas fontes (bloqueio de rede ou WAF por país; não tentamos contornar):

1. **Portal da Transparência de Belém (GIIG)**: a fonte de pagamentos por fornecedor. É a dúvida crítica.
2. **Diário Oficial do Município** (`diario.belem.pa.gov.br`, `sistemas.belem.pa.gov.br/diario`). O Querido Diário parou em 13/05/2025.
3. **BelémPrev** e qualquer outro `*.belem.pa.gov.br` (folha, Prefeitura e CODEM).
4. **Mural de Licitações do TCM-PA** (Cloudflare 403 fora do Brasil). Também atinge os acórdãos e as consultas no `tcmpa.tc.br`.
5. **API do IBGE** (`servicodados.ibge.gov.br`): é contornável pelo `geoftp`.

Opções: uma VPS pequena em São Paulo (Magalu Cloud, Locaweb, AWS/GCP/Azure sa-east-1, Oracle Free Tier em Vinhedo/SP) **ou** rodar os coletores a partir de uma conexão residencial no Brasil. Atenção: o bloqueio da CINBESA pode ser por país e não por ASN de datacenter; o check-host em São Paulo (AS268581, um provedor brasileiro) passou. Testar a VPS brasileira **antes** de contratar por um período longo.

Funcionam da VPS nos EUA: PNCP, SICONFI, CNPJ da Receita, download do CEIS/CNEP, TSE, Querido Diário (só até 2025), IOEPA, site e API da Câmara, GIIG da Câmara, geoftp do IBGE, BrasilAPI e minhareceita.

---

## Respostas da seção 9.2

1. **O Portal de Belém está atualizado ou parou em 31/12/2024?** **Não deu para responder daqui:** o portal só aceita conexões do Brasil e o Wayback não tem capturas úteis (uma, de 15/05/2025). Indícios: o **mesmo sistema GIIG**, na instância da Câmara, está atualizado até **19/10/2026**; e a Prefeitura entrega o SICONFI em dia (RREO do 4º bimestre/2026 homologado), ou seja, a contabilidade de 2026 existe. Se o GIIG da Prefeitura estiver parado, seria por falha de publicação, não por falta de dado. **É a primeira coisa a checar da VPS brasileira** (ler a "Última Data de Movimentação" na página de despesas).
2. **Exportação ou só tela? Como raspar o WebForms?** Na instância da Câmara: só tela, sem botão de CSV. A raspagem funciona com **HTTP puro, sem Playwright**: GET → `__VIEWSTATE`, `__VIEWSTATEGENERATOR`, `__EVENTVALIDATION` e `__PREVIOUSPAGE` → POST com `...wuc_DataInicio$txtData` e `...wuc_dataFim$txtData` em `dd/mm/aaaa` e `ctl00$Content$btnbuscar=Buscar`. Os detalhes vêm por `IdEmpenho`; a paginação é postback (`__EVENTTARGET`), ainda a implementar. Script: `scripts/fase0_giig_postback.py`. Falta confirmar que a instância da Prefeitura é igual (provável, pelos caminhos `.aspx` do handoff).
3. **Quanto dos contratos de Belém está no PNCP?** Parcial e provavelmente baixo: **147 contratos municipais com ano de 2026** e 288 vigentes em 2026, somando todos os órgãos municipais indexados (15 CNPJs). Só a Câmara tem 9 contratos de 2026 no próprio site, e **nenhum contrato da Câmara aparece nos 341 registros baixados do PNCP** (falta a página 4, que o servidor recusa). A comparação com o Diário e o Mural fica para a VPS brasileira.
4. **O Mural do TCM-PA tem consulta pública sem login e exportação?** Bloqueado fora do Brasil (Cloudflare 403). Do Brasil responde 200; login e exportação seguem sem verificação.
5. **O Querido Diário cobre Belém?** Sim, de **01/02/2005 a 13/05/2025** (4.744 edições). **Nada de 2026.** API nova em `api.queridodiario.org.br`.
6. **Onde está o download do CNPJ e qual o layout?** No Nextcloud da Receita: `arquivos.receitafederal.gov.br`, share `gn672Ad4CF8N6TK`, caminho `Dados/Cadastros/CNPJ/AAAA-MM/` (WebDAV `public.php/webdav/`). O mês de 2026-10 saiu em 13/10. O layout não mudou: Empresas, Estabelecimentos e Socios em 10 partes cada, mais Simples e as tabelas de domínio, ≈ 7,8 GB zipados. Atenção: segundo a imprensa, o **CNPJ alfanumérico** começou em jul/2026 (IN RFB 2.229; não conferido na fonte), então a chave deixa de ser só numérica. Tratar o CNPJ como texto de 14 caracteres.
7. **Bloqueiam datacenter? Precisam de limite de taxa ou User-Agent?** Sim, bloqueiam: a rede da Prefeitura (CINBESA) e a API do IBGE derrubam no TCP; o TCM-PA bloqueia por WAF da Cloudflare; o Portal federal manda desafio do AWS WAF nas páginas. Nenhuma fonte que funcionou exigiu User-Agent especial. Nenhuma respondeu 429, mas o PNCP é lento e reseta conexões. Manter ≥ 1 s por host, timeout de 90–150 s no PNCP e nova tentativa com espera.
8. **A folha de Belém é nominal? Onde?** Não verificável daqui (portal da Prefeitura bloqueado). A Câmara publica folha no próprio site.
9. **Existe malha oficial de bairros aberta?** Sim: **IBGE, Censo 2022, bairros (SHP/GPKG)**, com 71 bairros de Belém e os 8 distritos. A malha da Prefeitura/CODEM não foi testada (bloqueada).
10. **O CNPJ 05.055.009/0001-13 é da Prefeitura? E a indireta?** **Sim** (Receita via BrasilAPI, SICONFI e PNCP). CNPJs municipais vistos no PNCP (contagem de contratos entre parênteses): SEMEC `05055033000152` (147), Guarda Municipal `49159407000155` (40), Município `05055009000113` (35) e a filial `05055009000628` (4), SEGBEL `59815458000141` (29), Saneamento `04789822000154` (26), SESMA `07917818000112` (13), Fundação Papa João XXIII `05065644000181` (12), SEFIN `05055025000106` (10), Secretaria da Mulher `59870569000150` (9), Instituto de Previdência `29331615000182` (7), SECONT `09551008000110` (4), SECOM `59693965000150` (3), Economia `10245579000106` (1), Planejamento e Gestão `14700173000127` (1). **Não aparecem** (verificar): SEURB, SEMOB, FUNPAPA, Fundo Municipal de Saúde, BelémPrev, CINBESA, Câmara e outros. Unidades sob o CNPJ da PMB: `925387` (Prefeitura), `927398` (Gabinete), `925905` (SEURB), `926327` (Assuntos Jurídicos), `930684` (Agência Distrital de Mosqueiro).
11. **Como tratar os fundos municipais?** No PNCP, os contratos saem no CNPJ da secretaria (SESMA, SEMEC), não no do fundo. No SICONFI está tudo consolidado no ente. Proposta: uma tabela `orgaos` com CNPJ, nome, tipo (direta, autarquia, fundação, fundo, empresa, Câmara) e "órgão-pai", preenchida pelo PNCP e depois pelo GIIG (combo "Entidade Governamental"). O agrupamento por secretaria fica a cargo do órgão-pai.
12. **Como desambiguar sócio PF com nome e CPF mascarado?** Usar a chave (nome normalizado + 6 dígitos centrais do CPF), que é o que a Receita publica. Na prática, quase não há colisão dentro de um município. Reforçar com co-ocorrência (mesma empresa, mesmo endereço, faixa etária do QSA). Nunca publicar o fragmento de CPF (LGPD, handoff §3); o fragmento fica só na base interna, como chave.

---

## Ordem sugerida a partir daqui

1. **VPS (ou proxy) no Brasil**, para o GIIG da Prefeitura (data de movimentação, 2026, estrutura), o Diário e o Mural do TCM-PA.
2. **PNCP completo**: lista de CNPJs municipais pela busca, depois `/v1/contratos` por CNPJ para 2024–2026 (os vigentes em 2026), mais itens e termos aditivos.
3. **CNPJ + CEIS**: baixar o mês 2026-10 (≈ 7,8 GB) para o DuckDB, filtrar pelos fornecedores do PNCP e cruzar com o CEIS.

# RuleTrace

**Qual regra valia nesta data, para esta categoria, e onde ela está escrita?** RuleTrace é um assistente RAG de um festival fictício. Combina regulamentos versionados com uma consulta de inscrição de somente leitura. Uma resposta precisa apontar para trechos recuperados; quando falta evidência, o sistema se abstém.

## Demonstração local

Requer Python 3.11+, Docker e Docker Compose. O modelo de geração e o de embeddings somam cerca de 3 GB de download, além das imagens. A inferência é local e pode demorar em CPU, principalmente na primeira consulta.

```sh
python3 scripts/bootstrap.py
docker compose up -d --build --wait
docker compose exec -T ollama ollama pull embeddinggemma
docker compose exec -T ollama ollama pull qwen3:4b-instruct-2507-q4_K_M
docker compose --profile ops build index
docker compose run --rm --no-deps index
python3 scripts/demo.py
```

A demo verifica três cenários: a inscrição `EVT-042` sob a regra retificada, a regra antiga em maio e uma pergunta sem fonte. A API local tem OpenAPI em `http://127.0.0.1:8120/docs`.

```sh
curl -sS http://127.0.0.1:8120/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Posso corrigir a inscrição EVT-042?","as_of":"2026-06-03"}'
```

## Como funciona

- **Ingestão** lê Markdown e PDFs textuais a partir de um manifesto local. Valida sobreposição de versões, caminhos e limites; mantém seção/página. Compara uma divisão por seção com janelas fixas sobrepostas dentro da mesma seção ou página.
- **Indexação** preserva chunks, metadados, embeddings e índice textual GIN em PostgreSQL. A geração é identificada pelo conteúdo, parâmetros de chunking e digest do embedding; o ponteiro ativo só muda junto com o commit da geração completa. Reingerir o mesmo corpus reutiliza a geração.
- **Recuperação** filtra vigência e categoria no banco antes de ranquear. A busca textual usa termos normalizados em português; a busca vetorial usa distância cosseno do pgvector. A híbrida funde rankings por RRF, sem comparar diretamente pontuações incompatíveis. A busca vetorial é exata: o corpus pequeno não justifica HNSW ou o trade-off de recall aproximado.
- **Tool calling** é limitado a uma consulta tipada `lookup_registration` com o mesmo ID que veio na pergunta ou no campo estruturado. O modelo não recebe shell, navegador ou SQL. A chamada de geração não recebe ferramentas.
- **Resposta** usa um prompt versionado e schema fechado. Citações são resolvidas no servidor somente a partir dos trechos desta consulta. Isso verifica a procedência do identificador, **não** garante que a fonte sustente cada afirmação. Consulte a [metodologia](docs/evaluation.md).

O backend usa FastAPI, LangChain Core, LangChain Text Splitters e a integração LangChain Ollama. O modelo é separado do índice, e a API roda com uma identidade PostgreSQL de leitura; o comando de ingestão usa uma identidade própria. As credenciais não são versionadas, o Postgres e Ollama não publicam portas e a API fica em loopback. Dados de inscrição são fictícios e a data da pergunta filtra **a regra**, não o histórico cadastral; a ferramenta retorna o status do fixture atual. Se atualizar o modelo de embeddings, rode a indexação novamente e reinicie a API para que ela reconheça a revisão ativa.

## Avaliação e testes

```sh
# Busca real + geração local; stdout é JSON.
docker compose exec -T api python -m ruletrace evaluate --generation-eval

# CI local sem baixar modelos: banco dedicado e testes determinísticos.
docker compose -p ruletrace-qa up -d --wait db
docker compose -p ruletrace-qa run --rm --no-deps --build checks
docker compose -p ruletrace-qa down --volumes
```

A CI configurada cobre validação de entradas, chunking, ferramentas e citações, além de testar SQL, vigência, permissões e persistência num PostgreSQL real. Os testes de integração usam vetores controlados; métricas de qualidade vêm da execução separada com modelos reais. Todo o corpus e o dataset de perguntas são fictícios e estão versionados.

## Limites

Não é um serviço implantado. Não há upload público, OCR, acesso a inscrições reais, nem automação para alterar inscrições. Os documentos são dados, não comandos. O sistema pode errar mesmo com uma referência válida; não é aconselhamento jurídico. Desligue a stack com `docker compose stop` para preservar os modelos e o índice.

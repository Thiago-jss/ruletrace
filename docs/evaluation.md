# Avaliação do RuleTrace

A suíte versionada em `evals/questions.json` inclui perguntas com fonte indicada, perguntas fora do corpus, um caso de texto não normativo e uma inscrição inexistente. A unidade relevante da busca é `(rule_id, version, locator)`, não o ID de um chunk. Isso permite comparar as duas estratégias de chunking sem atribuir relevância a IDs específicos de uma implementação.

- **Recall@4:** fração das perguntas com fonte em que o trecho correto apareceu entre os quatro primeiros. Há apenas uma fonte-alvo por pergunta neste conjunto.
- **MRR@4:** média de `1/rank` para a posição da primeira fonte correta; um item ausente vale zero.
- São comparados os seis pares de estratégia de busca e chunking na mesma geração do corpus. O vetor de cada consulta é reaproveitado no experimento; os tempos de busca reportados excluem embeddings e não são benchmark de carga.
- A avaliação da resposta usa o pipeline padrão (`hybrid` + `section`). Separa status de resposta/abstenção, presença da fonte esperada e verificação lexical de fatos-alvo. São sinais de regressão, não uma prova de correção semântica. Inspecione as respostas e trechos no JSON para verificar se o conteúdo citado sustenta a afirmação.
- Nenhum modelo é usado como juiz neste recorte. O conjunto é pequeno, construído com o corpus e não é uma estimativa de qualidade em produção.

## Reproduzir

```sh
mkdir -p reports
docker compose exec -T api python -m ruletrace evaluate --generation-eval > reports/local-evaluation.json
```

Sem `--generation-eval`, a saída contém apenas métricas de recuperação. O resultado registra geração, revisão do prompt, identificador do modelo de embeddings e digest do modelo de chat quando utilizado.

# Resultados locais — baseline v2

Execução com PostgreSQL/pgvector, `embeddinggemma` e `qwen3:4b-instruct-2507-q4_K_M` via Ollama. O [relatório JSON](../reports/baseline-v2.json) registra os digests, a geração do índice, a revisão do prompt e os resultados por caso. Os campos de pontuação foram recalculados sobre as respostas observadas após corrigir a checagem lexical: uma abstenção não pode ganhar crédito por conter a palavra “não”. As respostas do modelo não foram alteradas.

## Recuperação

Foram 10 perguntas com fonte, seis configurações e `k=4`. A mediana abaixo exclui embeddings e geração.

| Busca | Chunking | Recall@4 | MRR@4 | Mediana da busca |
| --- | --- | ---: | ---: | ---: |
| Textual | Seção | 1.00 | 0.8667 | 10.01 ms |
| Textual | Janela | 1.00 | 0.8250 | 8.83 ms |
| Semântica | Seção | 1.00 | 1.0000 | 10.91 ms |
| Semântica | Janela | 1.00 | 0.9500 | 10.76 ms |
| Híbrida | Seção | 1.00 | 0.9000 | 12.37 ms |
| Híbrida | Janela | 1.00 | 0.9333 | 12.34 ms |

As seis combinações encontraram a fonte esperada entre os quatro primeiros resultados. Neste corpus, a busca semântica por seção ranqueou melhor do que a híbrida. No caso `EVT-042`, por exemplo, a fonte ficou em primeiro na semântica por seção e em segundo na híbrida por seção. A API mantém o modo híbrido como padrão para demonstrar as duas modalidades, não por alegação de maior acurácia.

## Geração e abstenção

O pipeline padrão (`hybrid` + `section`) respondeu **8 de 10** perguntas com fonte. As oito citaram a fonte esperada e passaram pela checagem factual lexical. Nos **4 de 4** casos sem evidência suficiente, o sistema se absteve: vigência anterior ao corpus, assunto ausente, texto não normativo e inscrição inexistente. O tempo mediano somente da etapa de geração foi **37.4 s** em CPU nesta execução local; não é latência de produção, nem inclui recuperação ou ferramenta.

Duas perguntas tinham fonte e foram recusadas pelo modelo mesmo com a evidência no contexto:

| Caso | Evidência recuperada | Posição na busca padrão |
| --- | --- | ---: |
| “Como aviso que não vou participar mais?” | Art. 8 do manual: formulário de desistência e prazo. | 1 |
| “Posso transmitir em vídeo sem depender de uma conexão compartilhada?” | Art. 5 de apoio: banda dedicada para vídeo não é garantida. | 1 |

Esses exemplos mostram falsos negativos de **geração**, não ausência da fonte no índice. O corpus é pequeno e foi criado junto com as perguntas; isso não estima qualidade em produção. A checagem lexical e o acerto do documento não substituem revisão do suporte de cada afirmação. A [metodologia](evaluation.md) descreve as métricas e como reproduzir o experimento.

# Resultados locais de recuperação

Medição feita com PostgreSQL real, pgvector e `embeddinggemma` (digest `85462619ee72…`). A geração do índice foi `c54639225de9295f7cef4b82285704b92be992d8f4d4ec1c40454383d0eac6d9`. Foram 10 perguntas com referência, seis configurações e `k=4` em cada uma. Tempos abaixo incluem a consulta ao armazenamento, mas excluem embeddings e geração.

| Busca | Chunking | Recall@4 | MRR@4 | Mediana da busca |
| --- | --- | ---: | ---: | ---: |
| Textual | Seção | 1.00 | 0.8667 | 14.09 ms |
| Textual | Janela | 1.00 | 0.8250 | 13.84 ms |
| Semântica | Seção | 1.00 | 1.0000 | 19.92 ms |
| Semântica | Janela | 1.00 | 0.9500 | 19.26 ms |
| Híbrida | Seção | 1.00 | 0.9000 | 22.80 ms |
| Híbrida | Janela | 1.00 | 0.9333 | 22.35 ms |

Neste conjunto, todos os modos encontraram a fonte entre os quatro primeiros resultados. A busca semântica por seção colocou a fonte em primeiro em todas as perguntas e teve MRR superior à busca híbrida. No caso da inscrição `EVT-042`, por exemplo, o primeiro resultado correto ficou em primeiro na busca semântica por seção e em segundo na híbrida por seção. Isso não estabelece um vencedor em produção: o corpus é pequeno e os casos foram criados junto com os documentos. O padrão da API continua híbrido para demonstrar as duas modalidades, não por alegação de maior acurácia.

O [procedimento de avaliação](evaluation.md) compara as mesmas perguntas sob o mesmo índice e separa recuperação e geração.

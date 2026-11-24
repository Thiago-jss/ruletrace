# Fronteiras e decisões

## Uma consulta

1. O FastAPI valida o contrato e delega a consulta ao serviço de resposta. Datas são explícitas para reproduzir consultas históricas.
2. Se um único identificador de inscrição foi fornecido, há uma etapa curta de tool calling. O modelo recebe apenas esse identificador, não o corpus nem a pergunta livre. O executor valida cardinalidade, nome, formato e correspondência dos argumentos antes de consultar os fixtures. A ferramenta lê três campos públicos do cenário fictício.
3. A categoria da inscrição, quando há consulta, vem do fixture. O banco aplica categoria e vigência `[início, fim)` igualmente às duas estratégias. A camada de recuperação controla seleção, ranqueamento e corte dos resultados.
4. A geração recebe evidências e dados de contexto como dados, sem ferramentas vinculadas. A API resolve apenas IDs presentes nos resultados desta consulta. Ausência de fonte não é o mesmo que falha de infraestrutura: a primeira produz abstenção, a segunda produz erro HTTP 503 sem detalhes do backend.

## Ingestão fora da API

O operador indexa um corpus local versionado. A API nunca baixa uma URL informada pelo usuário nem aceita upload. O leitor do banco não consegue ativar outra geração. Cada ingestão calcula uma identidade reproduzível pelo conteúdo, configuração e revisão do embedding. Somente após todas as gravações o ponteiro passa a apontar para a nova geração. Gerações antigas permanecem acessíveis internamente para requisições que já capturaram o snapshot; a demo não aplica retenção automática.

## Riscos residuais

O prompt reduz o risco de obedecer instruções nos documentos; não é uma fronteira de segurança. O que impede o efeito privilegiado é a arquitetura: a etapa que lê documentos não tem ferramentas de escrita nem de rede, a etapa de tool calling não recebe documentos e o backend valida a única chamada admitida. As citações ainda precisam de avaliação de suporte textual. A rede local e o corpus fictício limitam o escopo desta demo; dados reais exigiriam identidade e autorização por registro, revisão do parser, limites de recurso e políticas de retenção.

# Composição histórica da carteira BOVESPA

O objetivo desse projeto é construir ao longo do tempo um banco de dados com os dados históricos da composição da carteira teórica do Índice Bovespa.

A B3 divulga antes de cada pregão a composição da carteiras teóricas dos índices, porém não disponibiliza uma maneira direta de obter os dados históricos das carteiras teóricas. Nesse projeto um componente acessa a página onde a B3 divulga a composição da carteira teórica ([https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-amplos/indice-ibovespa-ibovespa-composicao-da-carteira.htm]), realiza o download do arquivo CSV e o envia para um bucket bruto do GCS (Google Cloud Storage). Após o upload para o GCS, um outro script será acionado para realizar o "parsing" do arquivo CSV e gravar a carteira resultante em um banco de dados que armazenará a série histórica

A ideia consiste em rodar a automação nos dias úteis, de segunda a sexta-feira, antes do início de cada pregão. O código do projeto foi ajustado para rodar como uma aplicação serverless do Cloud Run Services

ATENÇÃO: as dependências estão ajustadas para a versão 3.12 do Python
A codificação fo realizada com auxílio do Github Copilot usando o modelo Claude Haiku 4.5

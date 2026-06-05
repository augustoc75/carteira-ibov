# Composição histórica da carteira BOVESPA

O objetivo desse projeto é construir ao longo do tempo um banco de dados com os dados históricos da composição da carteira teórica do Índice Bovespa.

A B3 divulga antes de cada pregão a composição da carteiras teóricas dos índices, porém não disponibiliza uma maneira direta de obter os dados históricos das carteiras teóricas. Nesse projeto um componente acessa a URL onde a B3 divulga a composição da carteira teórica ([https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-amplos/indice-ibovespa-ibovespa-composicao-da-carteira.htm]), realiza o download do arquivo CSV e, após realizar o "parsing" do arquivo CSV, grava a carteira resultante em um banco de dados que armazenará a série histórica

A ideia consiste em rodar a automação nos dias úteis, de segunda a sexta-feira, antes do início de cada pregão. O código do projeto pode rodar tanto em um servidor local quanto em um container de uma aplicação serverless em uma plataforma de nuvem. Para fins didáticos escolhi a GCP.

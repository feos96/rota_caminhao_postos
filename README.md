# 🛣️ Roteirização de Caminhões com Postos Próximos à Rota

Este projeto utiliza a API do OpenRouteService, Overpass e geocodificação para traçar uma rota otimizada para veículos pesados, identificando postos de combustível em um raio de até 5 km da rota.

## 🔧 Tecnologias e bibliotecas usadas

- Python 3
- Folium
- OpenRouteService
- Overpass API (via requests)
- Geopy
- Shapely
- NumPy

## 🚚 Funcionalidades

- Cálculo de rota entre duas cidades com restrições para caminhões (altura, peso, etc)
- Busca automática de postos próximos via Overpass API
- Filtro geográfico com Shapely para encontrar apenas os postos dentro de 5 km da rota
- Geração de mapa interativo com a rota e os postos filtrados

## ▶️ Como usar

1. Clone este repositório:
   ```bash
   git clone https://github.com/seu-usuario/rota_caminhao_postos.git
   cd rota_caminhao_postos
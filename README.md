# 🛣️ Roteirização de Caminhões com Postos Próximos à Rota

![Mapa da Rota](img/rota.png)

Este projeto utiliza a API do OpenRouteService, Overpass e geocodificação para traçar uma rota otimizada para veículos pesados, identificando postos de combustível em um raio de até 1 km da rota.

---

## 🔧 Tecnologias e Bibliotecas Usadas

- Python 3
- Folium
- OpenRouteService
- Overpass API (via requests)
- Geopy
- Shapely
- NumPy
- Argparse
- Pandas

---

## 🚚 Funcionalidades

- Cálculo de rota entre duas cidades com restrições para caminhões (altura, peso, etc.)
- Busca automática de postos próximos via Overpass API
- Filtro geográfico com Shapely para encontrar apenas os postos dentro de 1 km da rota
- Filtro por nome de postos (ex: Ipiranga, Shell)
- Geração de mapa interativo em HTML com rota e postos
- Exportação dos postos encontrados em arquivo CSV
- Uso via terminal com argumentos customizáveis

---

## ▶️ Como Usar

### Clone o repositório:
```bash
git clone https://github.com/feos96/rota_caminhao_postos.git
cd rota_caminhao_postos

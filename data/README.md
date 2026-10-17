# Dados

Fonte: [Olist / Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), sob [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).

`manifest.json` registra os hashes SHA-256 dos cinco CSVs utilizados e as contagens de qualidade. Os CSVs brutos e o banco SQLite ficam somente no ambiente local, ignorados pelo Git. Execute `python scripts/build.py` na raiz para obtê-los.

O painel publica agregados transformados em `docs/data.json`, sob a mesma licença da fonte. Não publica comentários, IDs de clientes ou linhas transacionais individuais.

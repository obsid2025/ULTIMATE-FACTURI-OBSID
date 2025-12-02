# Ultimate Facturi OBSID

Dashboard web pentru procesarea si gruparea facturilor - versiune pentru OBSID SRL.

## Functionalitati

- **Parsare MT940**: Extrage automat incasarile din extrasele bancare MT940 (Banca Transilvania)
- **Procesare Borderouri**: GLS, Sameday
- **Procesare Netopia**: Tranzactii plati online
- **Potrivire Automata**: AWB-uri cu facturi din Gomag
- **Export Excel**: Raport complet cu facturi grupate pe OP-uri

## Surse de Incasari Detectate

- GLS (Transfer Ramburs)
- Sameday (Delivery Solutions)
- Netopia (BATCHID)

## Deploy pe Coolify

### 1. Configureaza variabilele de mediu

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=parola_sigura
ADMIN_NAME=Administrator
COOKIE_KEY=cheie_random_secreta
```

### 2. Deploy din GitHub

1. Conecteaza repo-ul GitHub in Coolify
2. Selecteaza branch-ul `main`
3. Seteaza variabilele de mediu
4. Configureaza domeniul: `dashboard.obsid.ro`
5. Deploy!

## Dezvoltare Locala

### Cerinte

- Python 3.11+
- pip

### Instalare

```bash
# Cloneaza repo-ul
git clone https://github.com/obsid2025/ULTIMATE-FACTURI-OBSID.git
cd ULTIMATE-FACTURI-OBSID

# Creeaza virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# sau
venv\Scripts\activate  # Windows

# Instaleaza dependentele
pip install -r requirements.txt

# Copiaza si configureaza .env
cp .env.example .env
# Editeaza .env cu credentialele tale

# Ruleaza aplicatia
streamlit run app/main.py
```

### Docker Local

```bash
# Build
docker-compose build

# Run
docker-compose up -d

# Logs
docker-compose logs -f
```

Aplicatia va fi disponibila la `http://localhost:8501`

## Structura Proiect

```
ULTIMATE-FACTURI-OBSID/
├── app/
│   ├── __init__.py
│   ├── main.py              # Aplicatia Streamlit principala
│   └── utils/
│       ├── __init__.py
│       ├── auth.py          # Sistem autentificare
│       ├── mt940_parser.py  # Parser fisiere MT940
│       ├── processors.py    # Procesoare GLS, Sameday, Netopia
│       └── export.py        # Generator export Excel
├── .streamlit/
│   └── config.toml          # Configurare tema Streamlit
├── uploads/                 # Fisiere incarcate (local)
├── exports/                 # Fisiere exportate (local)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Licenta

Proprietar - OBSID SRL

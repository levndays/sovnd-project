# СОВНД — Система оперативного виявлення несанкціонованого доступу

Курсова робота: прототип системи виявлення поведінкових аномалій на
рівні ядра Linux із використанням eBPF, гібридним сигнатурно-аномальним
скорингом та поясненням рішень (Explainable Scoring).

* **Виконавець:** Андрій Кондратюк, ІПЗм-12, ФІТ КНУ ім. Тараса Шевченка
* **Керівник:** к. т. н., доц. Олег Курченко
* **Рік:** 2026

## Швидкий старт

```bash
# 1. Встановлення (Linux ≥ 5.8 із BTF, clang, llvm, libbpf-dev)
git clone https://github.com/levndays/sovnd-project.git
cd sovnd-project
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Компіляція eBPF-програм та C-loader
make -C drivers/ebpf

# 3. Запуск стенду (потрібен root для CAP_BPF)
sudo python3 apps/demo.py start
# → http://localhost:8000  (дашборд із кнопкою симуляції атак)
```

Альтернатива — `docker-compose up` із каталогу `deploy/`.

## Що це

Гібридний детектор runtime-загроз із чотирма векторами сигналів:

| Компонент | Що дає | Реалізація |
| :---- | :---- | :---- |
| **signature** | швидкі IOC-збіги | `core/detection/signature.py` |
| **statistical** | Z-оцінка проти EWMA-базової лінії | `core/detection/statistical.py` |
| **graph** | евристики над provenance-графом | `core/graph/builder.py` |
| **n-gram** | рідкісні послідовності системних викликів | `core/metrics/engine.py` |

Підсумкова оцінка $S = \left(\sum_i w_i \cdot d_i\right) \cdot P_{\text{ctx}}$,
де $P_{\text{ctx}}$ — контекстний коефіцієнт за `comm` процесу.
Деталі — у [`coursework.md`](coursework.md) §2.2 та [`ARCHITECTURE.md`](ARCHITECTURE.md) §7.

## Структура репозиторію

```
sovnd-project/
├── apps/               точки входу (agent, server, demo)
├── core/               бізнес-логіка детектування
│   ├── config.py       ваги, пороги, IOC-патерни, P_ctx
│   ├── metrics/        EWMA-вектор M(t), n-грами
│   ├── detection/      signature + statistical детектори
│   ├── graph/          provenance-граф (NetworkX)
│   └── scoring/        зведення компонентів у Alert
├── drivers/ebpf/       kernel-side eBPF (C) + Python-міст
├── internal/           інфраструктура (Docker resolver, SQLite)
├── web/                статичний дашборд (Chart.js + WebSocket)
├── scripts/            performance-валідація, train-каркас
├── tests/              pytest (unit + integration, 281 тест)
├── docs/uml/           PlantUML-діаграми (Component, Sequence,
│                       Deployment, Use Case) — рисунки 3.1–3.4
├── deploy/             Dockerfile + docker-compose.yml
├── coursework.md       пояснювальна записка курсової
├── ARCHITECTURE.md     технічна архітектура (англ.)
└── APPENDIX.md         додаток для захисту
```

## Виміряна продуктивність

Референсний запуск (`scripts/validate_performance.py`, Linux 6.x,
3 повтори × 10 с, цільове навантаження 500 EPS):

| Параметр | Значення |
| :---- | ----: |
| CPU агента (одне ядро) | 86.6 % ± 2.7 % |
| Резидентна пам'ять | 49.3 МБ |
| Медіана латентності виявлення | 361 мс |
| p95 латентності | 501 мс |
| Точність (precision) | 100 % |
| Повнота (recall) | 75 % |

Однопотоковий Python-агент насичується за усталеної інтенсивності понад
~2000 EPS — це обмеження `user space`, не самого eBPF-зонду.

## Розробка

```bash
# Тести
pytest                            # 281 тест

# Лінт
ruff check .                      # 0 помилок при поточній конфігурації

# Перевірка продуктивності (вимагає запущеного агента)
sudo python3 apps/agent.py &
sudo -E python3 scripts/validate_performance.py --runs 3 --window 10
```

## Корисні посилання

* [`coursework.md`](coursework.md) — пояснювальна записка курсової (43 с.)
* [`ARCHITECTURE.md`](ARCHITECTURE.md) — деталі архітектури (англ.)
* [`APPENDIX.md`](APPENDIX.md) — додаток для захисту: карта репозиторію
* [`docs/uml/`](docs/uml/) — PlantUML-діаграми (рисунки 3.1–3.4)
* [`scripts/train.py`](scripts/train.py) — каркас навчання / валідації (TODO)

## Ліцензія

GPL-3.0-or-later. Курсова робота, розроблена у академічних цілях.

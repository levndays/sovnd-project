# ДОДАТОК А. Опис репозиторію та супровідних артефактів

Цей додаток фіксує організацію відкритого репозиторію курсової роботи,
відповідність файлів реалізації розділам пояснювальної записки, а також
команди для збірки, запуску та перевірки прототипу.

* **GitHub:** <https://github.com/levndays/sovnd-project>
* **Гілка:** `master`
* **Ліцензія:** GPL-3.0-or-later
* **Мови реалізації:** C (для простору ядра, eBPF) та Python 3.10+ (для простору користувача)
* **Цільова операційна система:** Linux із ядром ≥ 5.8 та підтримкою BTF

## А.1. Карта репозиторію

```
sovnd-project/                            ← корінь
│
├── apps/                                 точки входу
│   ├── agent.py                          ← головний детекційний цикл (T_main, §3.3.1)
│   ├── server.py                         ← FastAPI: REST + WebSocket + /metrics
│   ├── demo.py                           ← оркестратор однокомандного запуску
│   └── dashboard.py                      ← допоміжний Streamlit-перегляд (debug)
│
├── core/                                 бізнес-логіка детектування (§4.2)
│   ├── config.py                         ← ваги, пороги, IOC, CONTEXT_COEFFICIENTS
│   ├── metrics/
│   │   └── engine.py                     ← EWMA-вектор M(t), n-грами (§2.1)
│   ├── detection/
│   │   ├── signature.py                  ← regex IOC-фільтр (§4.2.1)
│   │   └── statistical.py                ← Z-score, euclid distance, n-gram report (§4.2.2)
│   ├── graph/
│   │   └── builder.py                    ← NetworkX provenance graph + 4 евристики (§4.2.3)
│   └── scoring/
│       └── engine.py                     ← формула S = (Σ wᵢ·dᵢ) · P_ctx (§4.3)
│
├── drivers/ebpf/                         ядрова підсистема
│   ├── src/
│   │   ├── tracer.bpf.c                  ← 9 tracepoint-обробників (§4.1.1)
│   │   ├── filter.bpf.c                  ← in-eBPF фільтр (cgroup / шлях / rate)
│   │   └── fd_tracker.bpf.c              ← життєвий цикл FD
│   ├── include/
│   │   ├── maps.bpf.h                    ← BPF-структури та мапи
│   │   ├── tracer.skel.h                 ← згенерована libbpf-скелетна обгортка
│   │   └── vmlinux.h                     ← BTF-розгортка для CO-RE
│   ├── loader/
│   │   └── loader.c                      ← C-API: start_loader / poll_events /
│   │                                       stop_loader / set_target_cgroup
│   ├── bridge.py                         ← ctypes-обгортка → libloader.so
│   └── Makefile                          ← clang + bpftool + ld → libloader.so
│
├── internal/                             інфраструктурні модулі
│   ├── container/
│   │   └── resolver.py                   ← cgroup-inode → Docker meta (§3.2 #11)
│   └── storage/
│       └── sqlite.py                     ← persist alerts + profiles
│
├── web/
│   └── index.html                        ← статичний дашборд (Chart.js + WS)
│
├── scripts/
│   ├── validate_performance.py           ← вимірювання продуктивності (§4.5.2)
│   ├── train.py                          ← каркас навчання / валідації порогу
│   ├── attack.sh                         ← генерація демо-атак
│   └── codegen.py                        ← допоміжна
│
├── tests/                                pytest-сюїта (281 тест)
│   ├── unit/                             — компонентні тести
│   ├── integration/                      — тести eBPF-збірки та API
│   └── conftest.py                       — спільні фікстури
│
├── docs/uml/                             PlantUML-діаграми (рисунки 3.1–3.4)
│   ├── fig-3-1-logical.puml              Component diagram
│   ├── fig-3-2-sequence.puml             Sequence diagram
│   ├── fig-3-3-deployment.puml           Deployment diagram
│   ├── fig-3-4-usecase.puml              Use case diagram
│   └── README.md                         — інструкції рендерингу
│
├── deploy/
│   ├── Dockerfile                        ← multi-stage build (clang → python:slim)
│   └── docker-compose.yml                ← sovnd-monitor + web-app
│
├── data/                                 ← (gitignored) runtime: SQLite, heartbeat,
│                                            perf_report.json
│
├── coursework.md                         ← пояснювальна записка курсової
├── ARCHITECTURE.md                       ← технічна архітектура (англ.)
├── README.md                             ← публічна сторінка GitHub
├── APPENDIX.md                           ← цей файл
├── pyproject.toml                        ← пакетування + pytest + ruff конфігурація
├── requirements.txt                      ← Python-залежності
└── .gitignore
```

## А.2. Відповідність файлів розділам пояснювальної записки

| Розділ записки | Зміст | Реалізація у репозиторії |
| :---- | :---- | :---- |
| §1.1 Обмеження ACL та auditd | теоретичне обґрунтування | — (літературний огляд) |
| §1.2 Технологія eBPF | теорія, CO-RE, BTF | використано у `drivers/ebpf/` |
| §1.3 FD як індикатор поведінки | теоретичне обґрунтування | реалізовано у tracepoints `tracer.bpf.c` |
| §1.4 Сигнатурний vs аномальний | таксономія підходів | гібрид у `core/scoring/engine.py` |
| §2.1 Профіль нормальної поведінки | $M(t) \in \mathbb{R}^7$, n-грами | `core/metrics/engine.py` |
| §2.2 Метод виявлення відхилень | формула $S$ та її компоненти | `core/scoring/engine.py` |
| §2.3 In-kernel фільтрація | дворівнева фільтрація | `drivers/ebpf/src/filter.bpf.c` + `apps/agent.py::NOISE_COMMANDS` |
| §3.1 Контекст за ISO/IEC/IEEE 42010 | вимоги до системи | задовольняються репозиторієм |
| §3.2 Логічний погляд | 12 компонентів | див. карту А.1 + `docs/uml/fig-3-1-logical.puml` |
| §3.3 Процесний погляд | 2 процеси, 3 потоки | `apps/agent.py` (T_poll + T_main) + `apps/server.py` |
| §3.4 Фізичний погляд | Docker-розгортання | `deploy/Dockerfile` + `docker-compose.yml` |
| §3.5 Розробницький погляд | шари модулів | див. карту А.1 |
| §3.6 Сценарії використання | 4 UCs | `docs/uml/fig-3-4-usecase.puml` |
| §3.7 Виворот вимог на компоненти | таблиця відповідності | таблиця 3.1 у записці |
| §3.8 Архітектурні рішення | 6 ADR | оформлено у §3.8 |
| §4.1 Реалізація компонентів | kernel + user space | `drivers/ebpf/` + `core/`, `internal/`, `apps/` |
| §4.2 Аналітичні модулі | sig + stat + graph + n-gram | `core/detection/`, `core/graph/`, `core/metrics/` |
| §4.3 Explainable Scoring | формула S з breakdown | `core/scoring/engine.py` |
| §4.4 Інтерфейс моніторингу | FastAPI + WebSocket | `apps/server.py` + `web/index.html` |
| §4.5.1 Сценарії тестування | 8 illustrative-атак | `apps/server.py::trigger_attack` |
| §4.5.2 Аналіз продуктивності | методика та результати | `scripts/validate_performance.py` + `data/perf_report.json` |

## А.3. Команди збірки, запуску, перевірки

### А.3.1. Збірка eBPF-програм

```bash
make -C drivers/ebpf clean
make -C drivers/ebpf           # → drivers/ebpf/libloader.so
                               #   drivers/ebpf/tracer.bpf.o
                               #   drivers/ebpf/include/tracer.skel.h
```

**Залежності збірки:** `clang ≥ 14`, `llvm`, `libbpf-dev`, `bpftool`.

### А.3.2. Запуск стенду

```bash
# Локально (рекомендовано для перевірки)
sudo python3 apps/demo.py start
# → відкриває http://localhost:8000 у браузері

# Через Docker
cd deploy && docker-compose up
```

### А.3.3. Перевірка тестами

```bash
source venv/bin/activate
pip install -r requirements.txt
python -m pytest -v             # 281 тест (unit + integration)
ruff check .                    # лінт (нуль попереджень при поточній конфігурації)
```

### А.3.4. Вимірювання продуктивності

```bash
# Термінал 1: запустити агента
sudo python3 apps/agent.py

# Термінал 2: запустити вимірювальну сюїту
sudo -E python3 scripts/validate_performance.py --runs 3 --window 10 --target-eps 500
# → результати у data/perf_report.json
```

### А.3.5. Рендеринг UML-діаграм

```bash
sudo pacman -S plantuml         # Arch
sudo apt install plantuml       # Debian/Ubuntu

plantuml docs/uml/*.puml        # → PNG за умовчанням
plantuml -tsvg docs/uml/*.puml  # → SVG для друку
```

## А.4. Виміряна продуктивність референсного запуску

Дані з `data/perf_report.json` після виконання
`scripts/validate_performance.py --runs 3 --window 10 --target-eps 500`
на хості Linux 6.x:

| Параметр | Значення | Примітка |
| :---- | ----: | :---- |
| CPU агента (одне ядро) | 86.6 % ± 2.7 % | основний обмежувач пропускної здатності |
| Резидентна пам'ять (RSS) | 49.3 МБ | стабільна між запусками |
| Спостережена пропускна здатність | 1674 ± 348 EPS | системний фон + стресор |
| Медіана латентності виявлення | 361 мс | від syscall до запису в БД |
| p95 латентності | 501 мс | у межах 2 Гц-кадру дашборду |
| Точність (precision) | 100 % | TP/(TP+FP) агреговано 9/9 |
| Повнота (recall) | 75 % | TP/(TP+FN) агреговано 9/12 |

Однопотоковий Python-агент насичується за усталеної інтенсивності понад
\~2000 EPS — деталі та інтерпретація у §4.5.2 пояснювальної записки.

## А.5. Напрями подальшого розвитку

Окреслені у пояснювальній записці; репозиторій містить підготовчу
інфраструктуру для двох із них:

1. **Автоматизований підбір порогу $T$ за цільовим FPR** —
   каркас у `scripts/train.py` (`collect → validate → tune-threshold`);
   усі три стадії оголошені, але вимагають реалізації.
2. **Багатопотокова процесна модель** — описана у §3.3.2; вимагатиме
   введення пулу обробників і дрібнозернистого блокування за PID-хешем
   (або переписування агента мовою Go / Rust).

## А.6. Історія розробки

Гілка `master` містить близько 50 змістовних комітів від першого
ескізу tracepoint-зонду до фінального полірування пояснювальної
записки. Хронологію можна переглянути у GitHub:

<https://github.com/levndays/sovnd-project/commits/master>

Або локально:

```bash
git log --oneline
```

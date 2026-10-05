# Лабораторна робота 2 — запуск у Windows без Docker

Це продовження TravelerAPI з лабораторної 1. У лабораторній 2 **заборонено Docker та віртуалізацію**: PostgreSQL, Python API і k6 працюють безпосередньо у Windows на одному комп'ютері. Попередні результати Hurl не є вимірюваннями k6. Числовий baseline та скриншоти потрібно отримати на вашому комп'ютері. У початковому звіті непроведені вимірювання позначені прямо.

## 1. Підготовка

1. Якщо старий API працює в Docker, зупиніть його командою `docker compose down` у його старій папці. Не додавайте `-v`: це видалило б дані. Після цього закрийте Docker Desktop через Quit і не запускайте WSL для цієї лабораторної.
2. Розпакуйте новий архів в окрему папку. Відкрийте папку, у якій безпосередньо є `app.py`, `native`, `tests` і `START_HERE_UA.md`.
3. У рядку адреси Провідника введіть `powershell` і натисніть Enter. Усі команди нижче, якщо не вказано інше, виконуються з цієї папки, а не з `.git`.
4. Перевірте Python: `py --version`. Якщо немає — встановіть Python для Windows з https://www.python.org/downloads/windows/ . Потрібен Python 3.12; команда `py -3.12 --version` має працювати. Проєкт містить lock-файл залежностей, перевірених у Python 3.12.
5. Встановіть **нативний PostgreSQL 16** із https://www.postgresql.org/download/windows/ . Оберіть PostgreSQL Server, pgAdmin та Command Line Tools. Залиште порт 5432, запам'ятайте пароль користувача postgres. Stack Builder для цієї роботи не потрібен. PostgreSQL 16 дозволить порівнювати той самий основний випуск, що й у лабораторній 1. Версія й параметри фіксуються перед тестом.
6. Встановіть k6:

```powershell
winget install k6 --source winget
```

Після встановлення закрийте PowerShell, відкрийте новий у папці проєкту та перевірте `k6 version`. npm для k6 не потрібний.

## 2. Створення локальної БД

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\native\init-db.ps1
```

Введіть пароль postgres, який ви вибрали в інсталяторі PostgreSQL. Скрипт знаходить psql у Program Files, створює окремого користувача `traveler_lab2` та БД `traveler_lab2`. Пароль postgres не друкується і видаляється зі змінної оточення після команди.

Для цього навчального локального проєкту облікові дані застосунку: traveler_lab2 / traveler_lab2_dev. Існуючий користувач не перезаписується: якщо він уже мав інший пароль, передайте власний DatabaseUrl у start-native.ps1. Запуск API автоматично створює таблиці зі schema.sql. Власні дані лабораторної 1 не видаляються.

## 3. Запуск API

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\native\start-native.ps1
```

При першому запуску через `py -3.12` створюється .venv і встановлюються залежності з requirements.lock.txt. Потім запускається один worker Uvicorn. Залиште це вікно відкритим.

У браузері відкрийте http://localhost:4567/health — має бути `{"status":"ok"}`. Документація доступна на http://localhost:4567/docs . Якщо порт зайнятий, зупиніть старий API. Якщо немає з'єднання з БД, перевірте Windows-службу PostgreSQL і пароль.

Для повторюваного baseline не змінюйте кількість worker, pool, версію БД чи паузи між тестами; зафіксуйте кожну зміну середовища. Не запускайте одночасно інші навантажувальні тести, Docker або важкі програми.

## 4. Запуск k6

Відкрийте другий PowerShell у папці проєкту.

Спочатку Smoke:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\performance-tests\run-tests.ps1 -Test smoke
```

Скрипт перевіряє, що порти API і БД належать процесам Python та PostgreSQL, записує версії й характеристики комп'ютера, а потім запускає k6. Службова телеметрія k6 вимкнена прапорцем --no-usage-report.

Якщо Smoke успішний, запускайте окремо:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\performance-tests\run-tests.ps1 -Test load
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\performance-tests\run-tests.ps1 -Test stress
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\performance-tests\run-tests.ps1 -Test spike
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\performance-tests\run-tests.ps1 -Test endurance
```

Endurance триває рівно 30 хвилин за профілем, плюс setup/teardown і завершення активних ітерацій. Стрес-тест проходить рівні до 1000 VU. Spike також має пік 1000 VU. Не запускайте ці команди одночасно.

Або запускайте всі п'ять одним скриптом:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\performance-tests\run-tests.ps1 -Test all
```

Послідовний повний запуск займає приблизно 47 хвилин плюс підготовка, паузи й cleanup. Під час Stress або Spike пороги можуть порушитися: код k6 99 фіксує цей результат, а скрипт продовжує збір. Інші помилки або невдалий Smoke зупиняють запуск.

Результати містяться у `tests\performance-tests\results`: `*-summary.json`, стислий `*-metrics.json.gz`, `*-console.txt`, `*-resources.csv`, `*-exit-code.txt`, `run-meta.json`. Повторний запуск переносить старі файли цього тесту в окрему папку previous-*, щоб вони не змішувалися.

При ручному запуску перейдіть у папку tests/performance-tests:

```powershell
cd .\tests\performance-tests
k6 run --no-usage-report --out json=results/smoke-metrics.json.gz smoke-test.js
```

Усі JS-імпорти локальні, k6 не завантажує допоміжні JS-бібліотеки з інтернету. Лише результати з **нативним PostgreSQL** придатні для baseline. Режим VERIFY=1 короткий і автоматично виключається із числового звіту; не використовуйте його для здачі Endurance.

## 5. Отримання готового Word-звіту з реальними результатами

Поверніться в корінь проєкту, де app.py. Один раз установіть залежності генератора:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\native\report-requirements.txt
```

Після запуску тестів виконайте:

```powershell
.\.venv\Scripts\python.exe .\native\build-report.py
```

Файл `TravelerAPI_Lab2_Report.docx` у корені проєкту буде оновлено: він отримає фактичні p95, середній час відповіді, частки помилок, таблиці етапів і графіки. Скрипт також створює analysis.json і phase-metrics.csv. Він не вигадує числа для тестів, які не запускалися.

Щоб додати скриншоти, після кожного тесту натисніть Win+Shift+S і збережіть зображення у results як `smoke-screenshot.png`, `load-screenshot.png`, `stress-screenshot.png`, `spike-screenshot.png`, `endurance-screenshot.png`. Повторіть build-report.py: зображення автоматично увійдуть у документ.

У таблицях max VU — найбільший **перевірений** прийнятний рівень, а не абсолютна межа системи. Breaking point має явно заданий критерій ≥5% помилок або p95 ≥2000 мс. Якщо критерію не досягнуто, це зазначається. Мережеві втрати й витік пам'яті не стверджуються лише за HTTP-метриками.

## 6. Git та коміти

Архів не містить зовнішньої вкладеної папки: app.py, native, tests і .git розташовані в корені. Історія з окремими комітами для розділів є в .git; резервна копія історії — у history.bundle. Не завантажуйте папку через Upload files: так історія загубиться.

Встановіть Git, якщо команда не розпізнається: `winget install --id Git.Git -e --source winget`; відкрийте новий PowerShell. З кореня нового проєкту виконайте:

```powershell
git log --oneline
git remote -v
git push -u origin lab2-corrected
```

origin налаштовано на ваш репозиторій https://github.com/Olyalya613/RSD_lab_1.git . Публікується окрема гілка lab2-corrected. main не переписується. Після авторизації відкрийте https://github.com/Olyalya613/RSD_lab_1/commits/lab2-corrected та додайте реальні посилання на коміти до звіту.

Якщо .git не збереглася при розпакуванні, з кореня розпакованого проєкту виконайте `git clone .\history.bundle ..\TravelerAPI_Lab2_git`, працюйте з цією відновленою копією й задайте `git remote set-url origin https://github.com/Olyalya613/RSD_lab_1.git`. Не запускайте git init поверх наявної історії.

## 7. Додаткові перевірки й зупинка

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_native_validation.py -v
```

П'ять тестів не потребують БД і перевіряють валідацію та регресію 404/400. Ще чотири перевірки аналізатора запускаються командою `python -m unittest discover -s tests -p test_analysis.py -v` через Python з .venv.

Щоб перевірити справжні одночасні HTTP-запити, залиште API запущеним і виконайте в другому вікні:

```powershell
$env:TEST_API_URL = 'http://127.0.0.1:4567'
$env:TEST_DATABASE_URL = 'postgresql://traveler_lab2:traveler_lab2_dev@127.0.0.1:5432/traveler_lab2'
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_concurrency.py -v
```

11 тестів створюють власні плани й видаляють їх після перевірки. Тести перевіряють CAS, конфлікт двох перестановок різних локацій, узгоджений знімок, rollback та роботу інших запитів, поки один UPDATE очікує замок. Не запускайте їх під час вимірювання k6. Якщо TEST_DATABASE_URL не задана, ця група позначається як skipped, а не як успішно виконана.

Для зупинки API натисніть Ctrl+C у першому вікні.

Бонусні завдання (CI, Grafana, ізоляція, кеш) не є частиною цього базового комплекту; обов'язкові п'ять сценаріїв реалізовані.

## 8. Новий контракт версій

- `travel_plans.version` захищає поля плану, `locations.version` — поля конкретної локації. Обидва PUT використовують SQL `WHERE id=%s AND version=%s`.
- `travel_plans.order_version` захищає склад і порядок колекції. GET плану повертає цей токен разом із локаціями в одному SQL-знімку.
- Для PUT локації зі звичайними полями (наприклад, notes) достатньо version. План не блокується явним замком; його version і order_version не змінюються.
- Коли в PUT є visit_order, обов'язково передайте також order_version з останнього GET плану. Застаріла версія порядку повертає 409 з current_order_version. Після конфлікту перечитайте план і повторно оцініть бажаний порядок.
- Додавання, видалення й успішна перестановка збільшують order_version. Пересунуті сусіди отримують нові locations.version. Видалення ущільнює visit_order до 1..N.
- Песимістичні замки батьківського плану залишені тільки для структурних змін; перестановка резервує його CAS за order_version. Звичайні PUT локації не роблять SELECT FOR UPDATE.
- Усі обробники БД оголошені def і виконуються в thread pool FastAPI. Асинхронна залежність тільки читає JSON-запит та не звертається до БД.

Приклад перестановки (значення version та order_version беруться з GET, числа нижче лише приклад):

```json
{"visit_order": 2, "version": 1, "order_version": 5}
```

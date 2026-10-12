# Лабораторна 3 — Docker і порівняння з лабораторною 2

Цей проєкт продовжує вашу опубліковану гілку lab2-corrected. API та всі п'ять k6-сценаріїв залишені такими самими. У results/baseline уже є ваші результати від 05.10.2026 з GitHub: PostgreSQL 18.4, Python 3.12.10, k6 2.2.0, Intel Core i5-8300H, 8 логічних процесорів, 15.86 ГБ RAM.

Контейнерних результатів до вашого запуску немає. Word-звіт показує справжній baseline і явно позначає відсутні Docker-вимірювання. Вихідні raw k6-потоки Lab 2 не були опубліковані; використовується збережений вами analysis.json без переобчислення та без зміни чисел.

## 1. Підготовка Windows

1. Розпакуйте ZIP у нову папку TravelerAPI_Lab3. У ній безпосередньо мають бути app.py, Dockerfile, docker-compose.yml, container, tests, results — без додаткової вкладеної папки.
2. Відкрийте PowerShell у цій папці: у рядку адреси Провідника введіть powershell.
3. Перевірте `py -3.12 --version`, `k6 version`, `hurl --version`, `git --version`.
4. Запустіть Docker Desktop і дочекайтеся готовності Engine. Якщо його немає, встановіть із https://docs.docker.com/desktop/setup/install/windows-install/ . Потрібні Linux containers. Не потрібно запускати Ubuntu вручну: команди виконуються у Windows PowerShell.
5. Перевірте `docker --version`, `docker compose version`, `docker info`. Якщо Engine не відповідає, не починайте збірку.
6. У вікні старого нативного API Lab 2 натисніть Ctrl+C: порт 4567 має бути вільним. Нативна база PostgreSQL на 5432 не конфліктує: контейнерна база НЕ публікує порт на Windows.

Не встановлюйте іншу версію k6 перед порівнянням: ваш baseline отримано на 2.2.0. Якщо k6 або обладнання змінилися, генератор позначить різні умови. Не запускайте навантажувальні тести паралельно.

## 2. Створіть приватний .env

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\container\setup-env.ps1
```

Скрипт генерує випадковий пароль контейнерної бази та узгоджений DATABASE_URL. Пароль не друкується. Існуючий .env не перезаписується. Для цієї нової БД НЕ потрібен пароль адміністратора вашого нативного PostgreSQL.

.env не додається в Git, образ чи ZIP. .env.example містить усі ключі та приклади. Якщо створюєте .env вручну, скопіюйте .env.example, замініть обидва входження REPLACE_WITH_YOUR_PASSWORD; спеціальні символи пароля в DATABASE_URL потребують URL-кодування. Генератор робить це автоматично.

## 3. Збірка та запуск

Для порівняння з нативним baseline використовуйте профіль benchmark:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\container\start-stack.ps1 -Profile benchmark
```

Команда збирає образ, запускає PostgreSQL та API, очікує healthy і показує compose ps. Базовий docker-compose.yml містить обмеження ресурсів. benchmark-override прибирає додаткові per-container CPU/RAM caps, щоб не порівнювати обмежений контейнер із необмеженим нативним процесом. Загальні ресурси Docker Desktop/WSL усе одно обмежують стек; вони записуються в метадані.

Еквівалентна команда:

```powershell
docker compose -f docker-compose.yml -f docker-compose.benchmark.yml up --build -d --wait
```

Звичайний обмежений профіль теж запускається однією командою, як вимагає завдання:

```powershell
docker compose up --build -d --wait
```

Не перемикайте профіль між тестами. Профіль dev з --reload призначений лише для розробки й не використовується для k6.

Відкрийте http://localhost:4567/health — очікується {"status":"ok"}. Swagger: http://localhost:4567/docs .

Якщо збірка зупинилася на завантаженні образу, перевірте доступ до Docker Hub. Для порівняння використано фіксовані випуски Python 3.12.10 та PostgreSQL 18.4, що відповідають вашому baseline. Зміна випусків потребує повторного baseline або окремого пояснення.

## 4. Hurl і моніторинг — обов'язкові скриншоти

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\container\check-stack.ps1
```

Скрипт перевіряє health, UID 1000 API та всі Hurl-файли. Очікується 5 успішних файлів. Він записує results/monitoring/hurl-console.txt і код завершення. Зробіть скриншот результату через Win+Shift+S і збережіть як results/monitoring/hurl.png.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\container\collect-monitoring.ps1
```

Вивід включає compose ps, останні журнали web і docker stats. Збережіть окремі PNG у results/monitoring:
- compose-ps.png
- web-logs.png
- docker-stats.png

Для живого перегляду, в окремому вікні:

```powershell
docker compose logs -f web
```

Ctrl+C завершує перегляд журналу, а не контейнери. Для stats двох сервісів:

```powershell
docker stats $(docker compose ps -q)
```

Ctrl+C завершує моніторинг. Зробіть також скриншот Docker Desktop Settings з доступними CPU/RAM або зафіксуйте ці значення у звіті. Моніторинг навантаження автоматично збирається кожним тестом.

## 5. Ті самі п'ять k6-тестів

Запускайте по одному, дочекавшись завершення й зберігши підсумковий скриншот.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\container\run-performance.ps1 -Test smoke
powershell -NoProfile -ExecutionPolicy Bypass -File .\container\run-performance.ps1 -Test load
powershell -NoProfile -ExecutionPolicy Bypass -File .\container\run-performance.ps1 -Test stress
powershell -NoProfile -ExecutionPolicy Bypass -File .\container\run-performance.ps1 -Test spike
powershell -NoProfile -ExecutionPolicy Bypass -File .\container\run-performance.ps1 -Test endurance
```

У results/docker збережіть smoke-screenshot.png, load-screenshot.png, stress-screenshot.png, spike-screenshot.png, endurance-screenshot.png. Не зберігайте їх у стару Lab 2 папку results.

Альтернатива — один послідовний запуск:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\container\run-performance.ps1 -Test all
```

Профілі: Smoke 20 с, Load 4 хв 30 с, Stress 9 хв, Spike 2 хв 24 с, Endurance 30 хв; сумарно приблизно 47 хв плюс setup/teardown, паузи й завершення ітерацій. k6 працює на Windows, як у Lab 2, а не в окремому контейнері.

Результати зберігаються окремо від baseline. Скрипт записує версії, фактичні ресурси Engine і контейнерів, хеші коду, summary, сирі метрики, консоль та docker stats. У кожного тесту є власний *-environment.json. Повторний запуск переносить старі результати цього тесту в previous-*.

VERIFY не використовується. LOAD_VUS, SPIKE_VUS і THINK_SECONDS потрібно прибрати зі змінних оточення, якщо ви їх задавали. Правильні 409 конфлікти рахуються окремо; вони не є неочікуваними HTTP-помилками. Невдалий Smoke зупиняє роботу. Порушення порогів Stress/Spike (k6 exit 99) зберігається як результат.

## 6. Отримайте Word-звіт

```powershell
py -3.12 -m pip install -r .\native\report-requirements.txt
```

Закрийте документ у Word і виконайте:

```powershell
py -3.12 .\container\build-report.py
```

Буде оновлено TravelerAPI_Lab3_Report.docx у корені. Він додасть реальні Docker-показники, зміни p95 та середнього часу у %, зміну частки помилок у процентних пунктах, графіки й скриншоти. Позитивна зміна часу означає повільніше, від'ємна — швидше. При нульовому початковому значенні відсоток не визначається.

Якщо код, версії чи профілі різні, автоматичного числового висновку про Docker не буде. Якщо відсутній тест або raw stream, він позначається як непроведений/неповний. Аналіз великих метрик Endurance може тривати кілька хвилин.

У вашому нативному Spike частка невдалих запитів становила близько 62.05%. Це реальний baseline, а не помилка Docker; у висновку його не слід замовчувати.

Baseline уже включено. Якщо маєте нові нативні результати, імпортуйте окремо, не перезаписуючи контейнерні:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\container\import-baseline.ps1 -SourceProject "C:\Users\admin\Downloads\TravelerAPI_Lab2_Corrected"
```

## 7. GitHub без зайвої зовнішньої папки

.git і history.bundle містять історію Lab 2 та нові коміти Lab 3. З кореня виконайте:

```powershell
git status
git log --oneline -8
git push -u origin lab3-docker
```

Після успішного push гілка: https://github.com/Olyalya613/RSD_lab_1/tree/lab3-docker . Не використовуйте Upload files для перенесення історії.

Щоб опублікувати готовий звіт і компактні результати:

```powershell
git add -f TravelerAPI_Lab3_Report.docx
git add -f "results/docker/*-summary.json" "results/docker/*-environment.json"
git add -f results/docker/analysis.json results/docker/run-meta.json results/comparison.json
git add -f "results/docker/*-screenshot.png" "results/monitoring/*.png" "results/monitoring/*.txt"
git commit -m "Add Docker measurements monitoring and comparison report"
git push
```

Спочатку переконайтеся, що ці файли існують. Не додавайте .env, .venv або великі raw-потоки в Git. Якщо .git загубилася при розпакуванні: `git clone .\history.bundle ..\TravelerAPI_Lab3_git`, потім у відновленій копії `git remote set-url origin https://github.com/Olyalya613/RSD_lab_1.git`.

## 8. Зупинка

```powershell
docker compose down
```

Дані в named volume зберігаються. Не додавайте -v, якщо не хочете видалити контейнерну БД. Нативна БД Lab 2 не змінюється.

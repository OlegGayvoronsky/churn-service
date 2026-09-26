# Задание 2.1

Зеленый прогон: https://github.com/OlegGayvoronsky/churn-service/actions/runs/36133640735

Ссылка на страницу с образом: https://github.com/OlegGayvoronsky/churn-service/pkgs/container/churn-service


# Задание 2.2

Ссылка на pull request: https://github.com/OlegGayvoronsky/churn-service/pull/3


# Задание 2.3

## 1. Конфигурация - путь к несуществующей модели

**Красный прогон:**  
https://github.com/OlegGayvoronsky/churn-service/actions/runs/36163168771

**Зелёный прогон после починки:**  
https://github.com/OlegGayvoronsky/churn-service/actions/runs/36163920127

Красным стал **job `deploy`**, ошибка произошла на шаге **подъёма сервиса** (`rollout status`).

В логе перед ошибкой:

```text
configmap/churn-config created
deployment.apps/churn-service created
deployment.apps/postgres unchanged
service/postgres unchanged
service/churn-service created
deployment.apps/churn-service image updated
Waiting for deployment spec update to be observed...
Waiting for deployment "churn-service" rollout to finish: 1 out of 2 new replicas have been updated...
error: timed out waiting for the condition
```

Статусы подов:

```text
churn-service-5b4648fc64-kf6qh   0/1   ImagePullBackOff
churn-service-5b4648fc64-qr46r   0/1   ImagePullBackOff
churn-service-684c9c4f65-kdmhw   0/1   CrashLoopBackOff
postgres-6fc55f99c7-zcm87        1/1   Running
```

В диагностике был:

```text
FileNotFoundError: [Errno 2] No such file or directory: 'artifacts/churn_catboost2.joblib'
```

По логу видно, что Kubernetes не смог завершить rollout: новые реплики не стали готовыми, а одна из реплик перезапускается с `CrashLoopBackOff`. Конкретная причина находится в диагностике - приложение пытается открыть файл модели, которого нет в контейнере.


---

## 2. Секрет - несовпадающее имя `secretRef`

**Красный прогон:**  
https://github.com/OlegGayvoronsky/churn-service/actions/runs/36165141399

**Зелёный прогон после починки:**  
https://github.com/OlegGayvoronsky/churn-service/actions/runs/36165883634

Красным стал **job `deploy`**, ошибка произошла на шаге **подъёма сервиса**.

В логе:

```text
Run kubectl apply -f k8s/
configmap/churn-config created
deployment.apps/churn-service created
deployment.apps/postgres unchanged
service/postgres unchanged
service/churn-service created
deployment.apps/churn-service image updated
Waiting for deployment "churn-service" rollout to finish: 0 out of 2 new replicas have been updated...
Waiting for deployment "churn-service" rollout to finish: 1 out of 2 new replicas have been updated...
error: timed out waiting for the condition
```

Статусы подов:

```text
churn-service-54c89d7c56-4tj8q   0/1   ImagePullBackOff
churn-service-54c89d7c56-x2kbf   0/1   ImagePullBackOff
churn-service-588f96fc75-kqt77   0/1   CreateContainerConfigError
postgres-6fc55f99c7-pv26r        1/1   Running
```

Диагностика:

```text
Error from server (BadRequest): container "api" in pod "churn-service-54c89d7c56-4tj8q" is waiting to start: trying and failing to pull image
```

По логу видно, что rollout не завершается, а один из новых подов имеет статус `CreateContainerConfigError`. Это указывает на ошибку конфигурации контейнера ещё до его запуска. В данном случае причина в том, что `Deployment` ссылается через `secretRef` на имя секрета, которое не совпадает с именем секрета, создаваемого pipeline.


---

## 3. Ресурсы - слишком большой `memory request`

**Красный прогон:**  
https://github.com/OlegGayvoronsky/churn-service/actions/runs/36166313889

**Зелёный прогон после починки:**  
https://github.com/OlegGayvoronsky/churn-service/actions/runs/36167015766

Красным стал **job `deploy`**, ошибка произошла на шаге **подъёма сервиса**.

В логе:

```text
configmap/churn-config created
deployment.apps/churn-service created
deployment.apps/postgres unchanged
service/postgres unchanged
service/churn-service created
deployment.apps/churn-service image updated
Waiting for deployment "churn-service" rollout to finish: 1 out of 2 new replicas have been updated...
error: timed out waiting for the condition
```

Статусы подов:

```text
churn-service-5d9449f476-bbfqp   0/1   Pending
churn-service-5d9449f476-krsqs   0/1   Pending
churn-service-6dfc4f569d-wtz9h    0/1   Pending
postgres-6fc55f99c7-zxvq2         1/1   Running
```

Диагностика:

```text
ничего
```

В этом случае причина видна по статусу `Pending`: pod создан, но Kubernetes не может назначить его на node. Если в `requests.memory` указано заведомо недоступное количество памяти, scheduler не может разместить pod на существующем узле. Поэтому rollout зависает и заканчивается по таймауту.


---

# Семь вопросов:

## 1.

Первый прогон: **1m6с** — [ссылка на прогон 1](https://github.com/OlegGayvoronsky/churn-service/actions/runs/36129557814).

Второй прогон: **20с** — [ссылка на прогон 2](https://github.com/OlegGayvoronsky/churn-service/actions/runs/36133640735).

Слои `COPY pyproject.toml uv.lock ./` и `RUN uv sync --frozen --no-dev --no-install-project` взяты из кэша (`CACHED`), потому что между прогонами не изменился ни pyproject.toml, ни uv.lock. Кроме того, все слои взяты из кеша, так как во втором прогоне поменялся только ci.yml файл на шагу smoke теста.


---

## 2.

Эти поды — kind пересоздаёт по старому манифесту до применения нового `kubectl set image`.

Это не ошибка, потому что rollout считается успешным по готовности пода актуального деплоя, а не по состоянию всех подов в кластере; `kubectl rollout status` дожидается перехода в Ready только нужных реплик.


---

## 3.

Путь: GitHub → Settings → Secrets and variables → Actions → secret `DB_PASSWORD` → в workflow передаётся как `${{ secrets.DB_PASSWORD }}` → шаг `kubectl create secret generic ... --from-literal=POSTGRES_PASSWORD=$DB_PASSWORD` создаёт Kubernetes Secret → под получает его через `secretRef` в манифесте deployment → значение доступно внутри контейнера как переменная окружения.

Пароль нельзя класть в `configmap.yaml`, потому что в таком случае он попадет в общий доступ.


---

## 4.

Если убрать `needs: tests`, то job `build` запускается независимо от результата `tests`, а значит, если тесты падают, образ всё равно соберётся и запушится в registry, а затем задеплоится в кластер. В результате в проде окажется версия с непроходящими тестами.


---

## 5.

За это отвечает строка `if: github.ref == 'refs/heads/main'` в job `build`.

Сделано так, потому что PR может прийти из ветки, которой ещё не доверяют полностью. Сборка и пуш образа в registry, а тем более деплой в кластер — это действия с побочным эффектом, которые не нужны и небезопасны на этапе ревью кода. Достаточно прогнать тесты и линтер, чтобы увидеть, что PR не ломает функциональность, а сборка и деплой происходят только после слияния с `main`.


---

## 6.

`pg_advisory_xact_lock` нужен, чтобы сериализовать выполнение инициализации БД - блокировка держится в рамках транзакции и гарантирует, что только один процесс одновременно выполняет эту инициализацию.

Без него при двух репликах и пустой базе обе реплики сервиса при старте одновременно попытаются выполнить `init()`, из-за чего происходит конфликт при параллельном создании одной и той же таблицы.

Как я уже сказал, реплики - несколько подов churn-service.


---

## 7.

Порядок (от раннего к позднему в жизни пода):

1. **Статус 1, Pending** — возникает на шаге подъема сервиса. **Планировщик не может подобрать ноду под запрошенные `requests`, поэтому под ещё не назначен ни на одну ноду**.

2. **Статус 2, CreateContainerConfigError** — возникает на шаге подъема сервиса. **Под уже назначен на ноду, но kubelet не может подготовить контейнер. В нашем случае он не может смонтировать несуществующий Secret**.

3. **Статус 3, CrashLoopBackOff** — возникает на шаге подъема сервиса. **Контейнер успешно стартовал, но процесс внутри падает после запуска. В нашем случае приложение не смогло найти файл модели по указанному в ConfigMap пути. В результате Kubernetes перезапускает контейнер по политике restart и счётчик рестартов растёт**.

Итоговый порядок отражает путь пода: сначала он должен быть запланирован на ноду (иначе Pending), затем должен быть успешно создан контейнер (иначе CreateContainerConfigError), и только потом, если создание прошло успешно, может проявиться ошибка уже внутри работающего приложения (CrashLoopBackOff).


# Задание 1*. Ускорение CI/CD пайплайна

## 1. Job `tests`: кэш uv по хэшу `uv.lock`

**Изменение:** добавлен явный ключ кэша зависимостей в шаге `setup-uv`:

```yaml
- uses: astral-sh/setup-uv@v7
  with:
    enable-cache: true
    cache-dependency-glob: "uv.lock"
```

**Замер:**

| | Время `uv sync --frozen` | Прогон |
|---|---|---|
| До | 2s | [run 36167015766](https://github.com/OlegGayvoronsky/churn-service/actions/runs/36167015766) |
| После | 2s | [run 36170040104](https://github.com/OlegGayvoronsky/churn-service/actions/runs/36170040104) |

Где смотрел: Actions → job `tests` → шаг `uv sync --frozen`.

**Вывод:** разницы не обнаружено. Это ожидаемо: в обоих прогонах `uv.lock` не менялся между запусками, то есть кэш и до изменения был тем же самым.


---

## 2. Job `build`: cache mount для uv в Dockerfile

**Изменение:** в Dockerfile добавлена директива `# syntax=docker/dockerfile:1` и cache mount в шагах установки зависимостей:

```dockerfile
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project
```

//... и аналогично во втором uv sync

**Замер:**

| | Время шага `uv sync --frozen --no-dev --no-install-project` | Прогон |
|---|---|---|
| До (без cache mount) | 7.6s | [run 36171457178](https://github.com/OlegGayvoronsky/churn-service/actions/runs/36171457178) |
| После (с cache mount, 2-й прогон подряд) | CACHED | [run 36174903262, job](https://github.com/OlegGayvoronsky/churn-service/actions/runs/36174903262/job/108203189486) |

Где смотрел: Actions → job `build` → шаг `docker/build-push-action` → строка `RUN uv sync --frozen --no-dev --no-install-project` (до) / `RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project` (после).

**Важное уточнение по замеру:** "после" — это второй прогон подряд после добавления `--mount=type=cache` (первый прогон после добавления был холодным, т.к. сам cache mount ещё не был наполнен). На втором прогоне buildx пометил шаг как `CACHED` — то есть слой не пересобирался вообще, весь layer-кэш (`type=gha`) сработал целиком, и шаг занял по сути 0s вместо 7.6s.


---

# Задание 2*. Доработка шага диагностики (`if: failure()`)

## Что изменил

Шаг переписан так, чтобы одним блоком покрывать все три причины падения:

```yaml
- name: диагностика
  if: failure()
  run: |
    echo "::group::Поды и их статус"
    kubectl get pods -o wide
    echo "::endgroup::"

    echo "::group::Deployments"
    kubectl get deploy -o wide
    echo "::endgroup::"

    echo "::group::События кластера (последние 50)"
    kubectl get events --sort-by=.lastTimestamp -o wide | tail -50
    echo "::endgroup::"

    for pod in $(kubectl get pods -o jsonpath='{.items[*].metadata.name}'); do
      echo "::group::describe pod/$pod"
      kubectl describe pod "$pod"
      echo "::endgroup::"

      echo "::group::Логи pod/$pod (текущий запуск)"
      kubectl logs "$pod" --all-containers --tail=100 || echo "нет текущих логов"
      echo "::endgroup::"

      echo "::group::Логи pod/$pod (предыдущий запуск, если был рестарт)"
      kubectl logs "$pod" --all-containers --previous --tail=100 || echo "нет логов предыдущего запуска"
      echo "::endgroup::"
    done
```

## Проверка

Диагностика проверена на 3-й поломке из базовой части (`requests.memory`, которой заведомо нет на узле):

**Красный прогон:**  
https://github.com/OlegGayvoronsky/churn-service/actions/runs/36179664044

Как и ожидалось для этого типа поломки:

- **логов пода нет** — ни текущих, ни предыдущих (контейнер не запускался, планировщик не смог разместить под на ноде);
- причина видна в блоках **"Поды и их статус"** (под в статусе `Pending`) и **`describe pod`** (событие `FailedScheduling: Insufficient memory`).

Это подтверждает, что для сценариев без запуска контейнера диагностика опирается на статус подов и `describe pod`/события кластера, а не на логи — ровно то поведение, которое и было целью доработки.


# Журнал ошибок

## 1. Ошибки в тестах

Прогоны:

https://github.com/OlegGayvoronsky/churn-service/actions/runs/36123572311

https://github.com/OlegGayvoronsky/churn-service/actions/runs/36128429448/job/108049832733

В run uv pytest в github actions нашел тексты ошибок:

```text
FAILED tests/test_integration.py::test_batch_prediction_is_logged - KeyError: 'Geography' - пытался в теле ответа получить фичу, хотя там фич быть и не должно. Поменял логику проверки.

LINE 1: SELECT model_version, score, response_codeFROM predictions W... - забыл пробел в запросе, из-за чего select...from склеились в одну строку.

assert db_row[0] == resp_row["request_id"]
AssertionError: assert UUID('0dec86df-ae8a-495e-945c-272c07a9be36') == '0dec86df-ae8a-495e-945c-272c07a9be36' - пытался сравнить uuid и str. В итоге просто обернул uuid в str.
```

---

## 2. Ошибка на smoke шагу в deploy

Прогоны:

https://github.com/OlegGayvoronsky/churn-service/actions/runs/36129557814

https://github.com/OlegGayvoronsky/churn-service/actions/runs/36133037717

Ошибку нашел в диагностике, в итоге пофиксил ошибки, которые я сделал на семинаре.
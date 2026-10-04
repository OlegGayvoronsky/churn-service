# Отчёт: churn-service
---

## Задание 1

![Задание 1, скриншот 1](<img width="1088" height="375" alt="image" src="https://github.com/user-attachments/assets/22b5e5b6-36db-4d64-a0f8-af1c45a0353a" />)

![Задание 1, скриншот 2](<img width="1280" height="686" alt="image" src="https://github.com/user-attachments/assets/78acabda-6b1b-4350-9be2-b0c1444ca336" />)

---

## Задание 2

![Задание 2, скриншот 1](<img width="1280" height="653" alt="image" src="https://github.com/user-attachments/assets/b556e6ef-d5f6-4608-82e9-46bd846b4721" />)

![Задание 2, скриншот 2](<img width="1280" height="91" alt="image" src="https://github.com/user-attachments/assets/7152f2f7-944b-463d-84d1-0de50bda2d58" />)

![Задание 2, скриншот 3](<img width="1280" height="94" alt="image" src="https://github.com/user-attachments/assets/c1ee2874-9cc6-469f-87e3-fc4ff32dd369" />)

![Задание 2, скриншот 4](<img width="1280" height="94" alt="image" src="https://github.com/user-attachments/assets/a11a3d11-8da1-4aef-8e78-917bd70043d0" />)

Чтобы выбрать `GATE_MIN_GAIN`, я посчитал std PR-AUC на 10 моделях, обученных с разными сидами, и взял gain в 2 раза больше, чем std. В результате новая версия становится чемпионом только при приросте, заметно превышающем шум обучения (std = `0.0016`, `GATE_MIN_GAIN` = `0.0032`).

---

## Задание 3

До отката:

![До отката](<img width="1168" height="402" alt="image" src="https://github.com/user-attachments/assets/d04986ff-065e-4137-99cd-767a5ef5e1f7" />)

После отката:

![После отката](<img width="1180" height="417" alt="image" src="https://github.com/user-attachments/assets/f968ffcc-6d63-4e84-8639-a8747a741c0c" />)

Прошло секунд 15, если считать вместе с затратами на написание команд.

---

## Задание 4

Зелёный прогон: <https://github.com/OlegGayvoronsky/churn-service/actions/runs/37040751556>

![Задание 4, скриншот](<img width="1280" height="322" alt="image" src="https://github.com/user-attachments/assets/660284fb-b206-4e79-b21e-272ce970200a" />)

---

## Задание 5

![Задание 5, скриншот 1](<img width="1280" height="80" alt="image" src="https://github.com/user-attachments/assets/18b20249-e7e9-45f6-b800-28b1bc3edb8b" />)

![Задание 5, скриншот 2](<img width="816" height="110" alt="image" src="https://github.com/user-attachments/assets/65f90e4f-d69d-49e2-848e-5f85814bf10f" />)

![Задание 5, скриншот 3](<img width="1280" height="247" alt="image" src="https://github.com/user-attachments/assets/61023ca5-0631-46ce-8e52-55d6d42533e9" />)

![Задание 5, скриншот 4](<img width="1002" height="800" alt="image" src="https://github.com/user-attachments/assets/305e1d3a-83a7-4150-8504-2384d986743c" />)

![Задание 5, скриншот 5](<img width="991" height="770" alt="image" src="https://github.com/user-attachments/assets/075c1890-e6be-47da-b597-a466bb546719" />)

---

## Задание 6

HPA в k9s:

![k9s hpa](<img width="687" height="210" alt="image" src="https://github.com/user-attachments/assets/c79c2dee-85c3-4597-9a4e-336e72aa0d0b" />)

События:

![События](<img width="1280" height="130" alt="image" src="https://github.com/user-attachments/assets/a197aef6-7538-4f93-bada-c538065876bb" />)

| Прогон | Пользователи | Реплики (макс) | p95, мс | CPU на под, m | requests CPU | RPS | Ошибки |
|---|---|---|---|---|---|---|---|
| 1 | 20 | 4 | 13 | 39 | 100m | 16.5 | 0 |
| 2 | 60 | 6 | 49 | 131 | 100m | 47.7 | 0 |
| 3 | 150 | 6 | 1600 | 916 | 100m | 85.1 | 5 |

На 150 пользователях один под выходит на ~900m. Из-за этой перегрузки пробы с коротким таймаутом начинают убивать поды. Поэтому появились 5 ошибок.

Requests до прогона: 256Mi, после: 200Mi.

---

## Задание 7

### 1) Неверный алиас модели

- Красный прогон: <https://github.com/OlegGayvoronsky/churn-service/actions/runs/37120414300>
- Зелёный прогон: <https://github.com/OlegGayvoronsky/churn-service/actions/runs/37121496862>
- Упало на шаге «сервис» с `error: timed out waiting for the condition`.
- Вывод ошибки в логах пода:

```text
mlflow.exceptions.RestException: INVALID_PARAMETER_VALUE: Registered model alias prod not found.
```

### 2) Неверное имя кластера

- Красный прогон: <https://github.com/OlegGayvoronsky/churn-service/actions/runs/37121780942>
- Зелёный прогон: <https://github.com/OlegGayvoronsky/churn-service/actions/runs/37121979632>
- Упало на шаге «kind, kubectl и доступ к кластеру»:

```text
ERROR: could not locate any control plane nodes for cluster named 'churn-trashservice'. Use the --name option to select a different cluster
```

### 3) Падение smoke

- Красный прогон: <https://github.com/OlegGayvoronsky/churn-service/actions/runs/37122576735>
- Зелёный прогон: <https://github.com/OlegGayvoronsky/churn-service/actions/runs/37123267880/job/111203555448>
- Упало на шаге smoke с `Error: Process completed with exit code 22`.
- Лога, который подробно описывает ошибку в диагностике, найти не смог.

---

## Задание 8

### 8.1

Потому что в процессе deploy нужен доступ к кластеру, запущенному у меня на компьютере за NAT. В случае тестов и build доступ к кластеру не нужен.

В качестве альтернативы можно открыть кластер наружу через туннель или поставить GitOps-агента, который сам забирает манифесты из репозитория. Но runner проще, так как он сам подключается к Github.

### 8.2

- `--network kind` нужен, чтобы runner находился в докер сети, где и кластер kind и мог обращаться к его сервисам.
- Docker socket нужен для управления докером с хоста, без него runner не сможет видеть контейнеры kind.
- `--group-add 0` даёт процессу доступ к сокету докера через группу `root`, без него на сокете могут быть ошибки доступа к Docker daemon.

### 8.3

Мы изменили для того, чтобы при последующих деплоях секрет обновлялся, а не создавался заново. Иначе будет ошибка при попытке создать секрет, так как секрет с таким именем уже существует.

### 8.4

champion - текущая лучшая модель, а challenger - новая модель, которая претендует стать лучшей. Сервис просит алиас, потому что в таком случае для смены модели можно просто переставить алиас в mlflow на другую модель и перезапустить поды. Поэтому откат модели через алиас не меняет больше ничего, кроме самой модели, в то время как rollout undo откатывает манифесты и версию кода контейнера.

### 8.5

Если задеплоить сервис в кластер, где никто ещё не обучил модель, то в таком случае деплой упадет на шаге сервиса, как было в задании 7, при указании неверного алиаса. Чтобы это увидеть, можно посмотреть в логи пода в k9s или сi, где будет написано:

```text
mlflow.exceptions.RestException: INVALID_PARAMETER_VALUE: Registered model alias prod not found.
```

### 8.6

Запрос из браузера к `http://mlflow.localhost` приходит на `127.0.0.1:80`, затем перенаправляется на порт `30080` ноды. Затем traefik по ingress правилу отправляет запрос в Service `mlflow:5000`, который направляет его в под mlflow на `targetPort 5000`.

`--allowed-hosts` ограничивает допустимые значения хостов. `--cors-allowed-origins` разрешает браузерные запросы с указанного адреса. Порт 80 задаётся при создании kind-кластера, потому что `extraPortMappings` настраивает проброс порта хоста в контейнер kind-ноды, а не является обычным Kubernetes-ресурсом. Порт 80 до создания кластера задается, чтобы выполнить проброс с порта 80 хоста на порт контейнера ноды 30080, после создания кластера выполнить пробросс не получится.

### 8.7

Если считать для прогона с 60 пользователями по таблице сверху (уже для 6 реплик):

Получится 6 * 131% / 60 с округлением вверх, что примерно равно 14. Но поскольку количество реплик ограничено сверху 6-ю, поэтому число репоик не поменялось. Вниз реплики уходили дольше из-за задержки в 5 минут, чтобы потом не пришлось заново поднимать реплики при кратковременном спаде.

### 8.8

В git лежит .dvc файл с хэшом, который позволяет получить доступ к файлу, который лежит в DVC.

Чтобы получить доступ к соответствующим данным нужно:

- получить md5 хэш данных, на которых обучалась модель версии N;
- найти коммит, где .dvc-файл содержал этот хеш;
- затем подтянуть соответствующий этому коммиту .dvc файл из репозитория по команде git checkout;
- запулить нужные данные из DVC хранилища при помощи uv run dvc pull.

---

## Звёздочка 1

- Без деплоя: <https://github.com/OlegGayvoronsky/churn-service/actions/runs/37040586764>
- С деплоем: <https://github.com/OlegGayvoronsky/churn-service/actions/runs/37040751556>

---

## Журнал ошибок

### 1) Неправильное имя модели в ConfigMap

Сервис искал в реестре не ту модель, которая была зарегистрирована.

### 2) Другая команда запуска раннера

Git Bash переписывал путь `/var/run/docker.sock`, поэтому путь к сокету пришлось указать с двойным слешем (`//var/run/docker.sock`). Рабочая команда:

```bash
docker run -d --name gh-runner --network kind --group-add 0 --restart unless-stopped \
  -v //var/run/docker.sock:/var/run/docker.sock \
  -e REPO_URL=https://github.com/OlegGayvoronsky/churn-service \
  -e RUNNER_TOKEN=<токен> \
  ghcr.io/actions/actions-runner:2.337.0 \
  bash -c '[ -f .runner ] || ./config.sh --unattended --url $REPO_URL --token $RUNNER_TOKEN --name churn-service-kind --labels kind; ./run.sh'
```

### 3) Забыл `\` и `-` в команде подтягивания секретов

Без `\` в конце строки команда `kubectl create secret` выполнялась без `--dry-run=client`, а без `-` после `-f` у `kubectl apply` не было аргумента.

### 4) Пароль в Postgres не совпадал с секретом

Пароль в уже запущенном postgres поде не совпадал с паролем в secrets на github. Добавил в `ci.yml`:

```yaml
      - name: пароль в базе = секрет
        env:
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
        run: |
          echo "ALTER USER postgres PASSWORD :'pw';" | \
            kubectl exec -i deploy/postgres -- psql -U postgres -v pw="$DB_PASSWORD"
```

А также пришлось принудительно поменять пароль в github secrets и для пода на один и тот же:

```bash
kubectl exec deploy/postgres -- psql -U postgres -c "ALTER USER postgres PASSWORD '<DB_PASSWORD>'"
kubectl rollout restart deploy/churn-service
```

### 5) Поле `replicas` в Deployment

Убрал реплики в deployment, без этого smoke падал с ошибкой 4.

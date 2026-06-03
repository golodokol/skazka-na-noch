# Публикация репозитория на GitHub

## 1. Установить Git

1. Скачать: https://git-scm.com/download/win  
2. Установить с настройками по умолчанию.  
3. Перезапустить Cursor / терминал.  
4. Проверить: `git --version`

Опционально: [GitHub Desktop](https://desktop.github.com/) — если удобнее без командной строки.

## 2. Аккаунт GitHub

- Зарегистрироваться: https://github.com/signup  
- Включить 2FA (рекомендуется).

## 3. Репозиторий на GitHub (уже создан)

**URL:** https://github.com/golodokol/skazka-na-noch  

**Remote для push:**

```
https://github.com/golodokol/skazka-na-noch.git
```

Репозиторий сейчас пустой — нужно один раз залить локальную папку `Documents\skazka-na-noch`.

## 4. Первый коммит (PowerShell)

```powershell
cd $env:USERPROFILE\Documents\skazka-na-noch

git init
git add .
git status
git commit -m "Initial commit: product docs and MVP structure for Telegram bot"
```

Проверьте `git status`: в коммите **не должно** быть файла `.env` (он в `.gitignore`).

## 5. Привязать remote и отправить

```powershell
git branch -M main
git remote add origin https://github.com/golodokol/skazka-na-noch.git
git push -u origin main
```

При первом `push` GitHub попросит войти (браузер или Personal Access Token).

### Авторизация (если пароль не принимается)

GitHub не принимает пароль аккаунта для `git push`. Нужен **Personal Access Token**:

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)  
2. Generate new token → scope `repo`  
3. При `git push` в поле password вставить **токен**, не пароль от GitHub.

Или установить [GitHub CLI](https://cli.github.com/) и выполнить `gh auth login`.

## 6. Через GitHub Desktop (без команд)

1. File → Add local repository → папка `Documents\skazka-na-noch`  
2. Если Git не инициализирован — «create a repository»  
3. Commit summary → Commit to main  
4. Publish repository → выбрать имя и Private/Public  

## 7. Что не коммитить

Уже в `.gitignore`:

- `.env` (токены бота и API)
- `*.db`, `data/`
- `.venv/`, `__pycache__/`

Перед push: `git status` — убедиться, что секретов нет.

## 8. Дальнейшая работа

```powershell
git add .
git commit -m "Описание изменений"
git push
```

## 9. Опционально

- **README** на GitHub подтянется из корневого `README.md`  
- **Topics** в настройках репо: `telegram-bot`, `bedtime-stories`, `mvp`  
- **Collaborators** — Settings → Collaborators, если работаете вдвоём

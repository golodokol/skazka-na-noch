# Безопасность

## Токен бота

- Храните **только** в `.env` (файл в `.gitignore`, не публикуйте в GitHub, чатах, скриншотах).
- Если токен попал в открытый доступ → [@BotFather](https://t.me/BotFather) → `/mybots` → ваш бот → **API Token** → **Revoke current token** → новый токен в `.env`.

## Перед `git push`

```powershell
git status
```

Убедитесь, что `.env` **не** в списке staged files.
